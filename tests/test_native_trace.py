"""Exercise the lab trace wrappers with a fake ioctl, never physical GPIO."""

import csv
import errno
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux-only lab trace")


DRIVER = r"""
#undef ioctl
#undef pthread_cond_timedwait
#define _GNU_SOURCE
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

struct gpio_values { uint64_t bits, mask; } __attribute__((aligned(8)));
#define SET_VALUES _IOWR(0xb4, 0x0f, struct gpio_values)
enum { THREADS = 4, PER_THREAD = 256 };
static atomic_int fake_calls;
static _Thread_local int expected_errno;

int pwm_trace_status(void);
int pwm_trace_ioctl(int, unsigned long, ...);
int pwm_trace_wait(pthread_cond_t *, pthread_mutex_t *, const struct timespec *);

/* This executable's ioctl replaces libc's symbol. No device is ever opened. */
int ioctl(int fd, unsigned long request, ...) {
    assert(request == SET_VALUES);
    assert(errno == expected_errno);
    va_list args;
    va_start(args, request);
    struct gpio_values *values = va_arg(args, struct gpio_values *);
    va_end(args);
    assert(values != NULL && values->mask == 1);
    atomic_fetch_add_explicit(&fake_calls, 1, memory_order_relaxed);
    if (fd == 11) { errno = EACCES; return -1; }
    if (fd == 12) { errno = EINTR; return -1; }
    if (fd == 13) { errno = ERANGE; return 7; }
    return 0;
}

static void call_ioctl(int fd, uint64_t bits, int before, int result, int after) {
    struct gpio_values values = { .bits = bits, .mask = 1 };
    expected_errno = before;
    errno = before;
    assert(pwm_trace_ioctl(fd, SET_VALUES, &values) == result);
    assert(errno == after);
}

static void check_trace_file(void) {
    const char *path = getenv("PWM_TRACE_PATH");
    char resolved[PATH_MAX + 1];
    assert(path != NULL && realpath(path, resolved) != NULL);
    DIR *directory = opendir("/proc/self/fd");
    assert(directory != NULL);
    struct dirent *entry;
    int matches = 0;
    while ((entry = readdir(directory)) != NULL) {
        char *end;
        long descriptor = strtol(entry->d_name, &end, 10);
        if (end == entry->d_name || *end || descriptor < 0 || descriptor > INT_MAX)
            continue;
        char link_path[64], target[PATH_MAX + 1];
        int length = snprintf(link_path, sizeof(link_path), "/proc/self/fd/%ld",
                              descriptor);
        assert(length > 0 && (size_t)length < sizeof(link_path));
        ssize_t used = readlink(link_path, target, sizeof(target) - 1);
        if (used < 0) continue;
        target[used] = '\0';
        if (strcmp(target, resolved)) continue;
        struct stat info;
        int flags = fcntl((int)descriptor, F_GETFD);
        assert(flags >= 0 && (flags & FD_CLOEXEC));
        assert(fstat((int)descriptor, &info) == 0);
        assert(S_ISREG(info.st_mode) && (info.st_mode & 0777) == 0600);
        matches++;
    }
    assert(closedir(directory) == 0);
    assert(matches == 1);
}

static void basic(void) {
    assert(pwm_trace_status() == 0);
    check_trace_file();
    call_ioctl(10, 5, EDOM, 0, EDOM);
    call_ioctl(11, 0, ENOENT, -1, EACCES);
    call_ioctl(12, 1, 0, -1, EINTR);
    call_ioctl(13, 0, EDOM, 7, ERANGE);
    assert(atomic_load(&fake_calls) == 4);

    pthread_condattr_t attributes;
    pthread_cond_t cond;
    pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
    assert(pthread_condattr_init(&attributes) == 0);
    assert(pthread_condattr_setclock(&attributes, CLOCK_MONOTONIC) == 0);
    assert(pthread_cond_init(&cond, &attributes) == 0);
    assert(pthread_condattr_destroy(&attributes) == 0);
    assert(pthread_mutex_lock(&lock) == 0);
    struct timespec deadline;
    assert(clock_gettime(CLOCK_MONOTONIC, &deadline) == 0);
    deadline.tv_nsec += 5000000;
    if (deadline.tv_nsec >= 1000000000) {
        deadline.tv_sec++;
        deadline.tv_nsec -= 1000000000;
    }
    uint64_t deadline_ns = (uint64_t)deadline.tv_sec * 1000000000ULL
        + (uint64_t)deadline.tv_nsec;
    errno = EBUSY;
    assert(pwm_trace_wait(&cond, &lock, &deadline) == ETIMEDOUT);
    assert(errno == EBUSY);
    assert(pthread_mutex_unlock(&lock) == 0);
    assert(pthread_cond_destroy(&cond) == 0);
    assert(pthread_mutex_destroy(&lock) == 0);
    printf("deadline_ns=%llu\nmain_tid=%ld\n",
           (unsigned long long)deadline_ns, syscall(SYS_gettid));
}

static void unavailable(int status) {
    assert(pwm_trace_status() == status);
    struct gpio_values values = { .bits = 1, .mask = 1 };
    errno = EDOM;
    assert(pwm_trace_ioctl(10, SET_VALUES, &values) == -1);
    assert(errno == status);
    assert(atomic_load(&fake_calls) == 0);
    pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
    pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
    struct timespec deadline = {0};
    assert(pthread_mutex_lock(&lock) == 0);
    errno = EDOM;
    assert(pwm_trace_wait(&cond, &lock, &deadline) == status);
    assert(errno == EDOM);
    assert(pthread_mutex_unlock(&lock) == 0);
    assert(pthread_cond_destroy(&cond) == 0);
    assert(pthread_mutex_destroy(&lock) == 0);
}

static void unknown(void) {
    assert(pwm_trace_status() == 0);
    errno = EDOM;
    /* No third argument: rejection must precede any unsupported vararg read. */
    assert(pwm_trace_ioctl(10, 0) == -1);
    assert(errno == EINVAL);
    assert(atomic_load(&fake_calls) == 0);
}

static void *thread_main(void *argument) {
    int fd = 100 + (int)(intptr_t)argument;
    for (int i = 0; i < PER_THREAD; i++)
        call_ioctl(fd, (uint64_t)(i & 1), EDOM, 0, EDOM);
    return NULL;
}

static void concurrent(void) {
    assert(pwm_trace_status() == 0);
    pthread_t threads[THREADS];
    for (int i = 0; i < THREADS; i++)
        assert(pthread_create(&threads[i], NULL, thread_main,
                              (void *)(intptr_t)i) == 0);
    for (int i = 0; i < THREADS; i++)
        assert(pthread_join(threads[i], NULL) == 0);
    assert(atomic_load(&fake_calls) == THREADS * PER_THREAD);
}

int main(int argc, char **argv) {
    assert(argc >= 2);
    if (!strcmp(argv[1], "basic")) basic();
    else if (!strcmp(argv[1], "unavailable")) {
        assert(argc == 3);
        unavailable(atoi(argv[2]));
    } else if (!strcmp(argv[1], "unknown")) unknown();
    else if (!strcmp(argv[1], "concurrent")) concurrent();
    else assert(!"unknown scenario");
    return 0;
}
"""


@pytest.fixture(scope="module")
def trace_executable(tmp_path_factory):
    command = shlex.split(os.environ.get("CC", "cc"))
    if not command or shutil.which(command[0]) is None:
        pytest.skip("lab trace tests need a C compiler")
    root = Path(__file__).resolve().parents[1]
    directory = tmp_path_factory.mktemp("native-trace")
    driver = directory / "driver.c"
    driver.write_text(DRIVER)
    executable = directory / "trace-driver"
    subprocess.run(
        [
            *command,
            "-std=c11",
            "-D_POSIX_C_SOURCE=200809L",
            "-Dioctl=pwm_trace_ioctl",
            "-Dpthread_cond_timedwait=pwm_trace_wait",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pthread",
            str(root / "tests/native_trace.c"),
            str(driver),
            "-o",
            str(executable),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return executable


def run_trace(executable, scenario, path=None, *arguments):
    environment = os.environ.copy()
    environment.pop("PWM_TRACE_PATH", None)
    if path is not None:
        environment["PWM_TRACE_PATH"] = str(path)
    result = subprocess.run(
        [str(executable), scenario, *map(str, arguments)],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def read_trace(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == [
            "seq",
            "kind",
            "tid",
            "fd",
            "level",
            "result",
            "begin_ns",
            "end_ns",
            "deadline_ns",
            "cpu_ns",
        ]
        return [
            {key: value if key == "kind" else int(value) for key, value in row.items()}
            for row in reader
        ]


def assert_complete(result, expected):
    summary = re.search(
        r"PWM_TRACE attempted=(\d+) written=(\d+) dropped=(\d+) "
        r"init_error=(\d+) io_error=(\d+) clock_error=(\d+)",
        result.stderr,
    )
    assert summary is not None, result.stderr
    assert tuple(map(int, summary.groups())) == (expected, expected, 0, 0, 0, 0)


def test_ioctl_results_errno_and_monotonic_timeout(trace_executable, tmp_path):
    path = tmp_path / "trace.csv"
    result = run_trace(trace_executable, "basic", path)
    metadata = dict(line.split("=", 1) for line in result.stdout.splitlines())
    rows = read_trace(path)
    assert_complete(result, 5)
    assert [row["seq"] for row in rows] == list(range(5))
    assert [row["kind"] for row in rows] == ["I", "I", "I", "I", "W"]
    assert [row["fd"] for row in rows] == [10, 11, 12, 13, -1]
    assert [row["level"] for row in rows] == [1, 0, 1, 0, -1]
    # ioctl trace results encode zero for success, errno for failure; pthread
    # results are direct return codes. The driver also checks actual returns.
    assert [row["result"] for row in rows] == [
        0,
        errno.EACCES,
        errno.EINTR,
        0,
        errno.ETIMEDOUT,
    ]
    assert {row["tid"] for row in rows} == {int(metadata["main_tid"])}
    assert all(row["tid"] > 0 for row in rows)
    assert all(
        row["begin_ns"] > 0 and row["end_ns"] >= row["begin_ns"] and row["cpu_ns"] > 0
        for row in rows
    )
    assert all(row["deadline_ns"] == 0 for row in rows[:-1])
    assert rows[-1]["deadline_ns"] == int(metadata["deadline_ns"])
    assert rows[-1]["end_ns"] >= rows[-1]["deadline_ns"]


@pytest.mark.parametrize("path_value", [None, ""], ids=["missing", "empty"])
def test_trace_path_is_required(trace_executable, path_value):
    result = run_trace(trace_executable, "unavailable", path_value, errno.EINVAL)
    assert "PWM_TRACE" not in result.stderr


def test_trace_file_is_exclusive(trace_executable, tmp_path):
    path = tmp_path / "existing.csv"
    path.write_text("preserve this existing file\n")
    result = run_trace(trace_executable, "unavailable", path, errno.EEXIST)
    assert path.read_text() == "preserve this existing file\n"
    assert "PWM_TRACE" not in result.stderr


def test_unexpected_request_is_not_forwarded(trace_executable, tmp_path):
    path = tmp_path / "unknown.csv"
    result = run_trace(trace_executable, "unknown", path)
    assert read_trace(path) == []
    assert_complete(result, 0)


def test_concurrent_records_are_complete_after_join(trace_executable, tmp_path):
    path = tmp_path / "concurrent.csv"
    result = run_trace(trace_executable, "concurrent", path)
    rows = read_trace(path)
    assert_complete(result, 4 * 256)
    assert [row["seq"] for row in rows] == list(range(4 * 256))
    assert Counter(row["fd"] for row in rows) == {fd: 256 for fd in range(100, 104)}
    assert {row["kind"] for row in rows} == {"I"}
    assert {row["result"] for row in rows} == {0}
    assert {row["deadline_ns"] for row in rows} == {0}
    tids = set()
    for fd in range(100, 104):
        group = [row for row in rows if row["fd"] == fd]
        assert Counter(row["level"] for row in group) == {0: 128, 1: 128}
        thread_tids = {row["tid"] for row in group}
        assert len(thread_tids) == 1
        assert next(iter(thread_tids)) > 0
        tids.update(thread_tids)
    assert len(tids) == 4
    assert all(
        row["begin_ns"] > 0 and row["end_ns"] >= row["begin_ns"] and row["cpu_ns"] > 0
        for row in rows
    )
