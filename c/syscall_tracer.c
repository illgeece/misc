// Minimal syscall tracer for macOS (x86_64) using system DTrace.
// - Launch a target (-c) or attach to -p <pid>
// - Visual, indented syscall trace, with user caller addresses
// Build: cc -Wall -O2 -o syscall_tracer syscall_tracer.c
// Usage:
//   sudo ./syscall_tracer /bin/ls -l
//   sudo ./syscall_tracer -p <pid>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <spawn.h>
#include <sys/wait.h>
#include <errno.h>

extern char **environ;

static void die(const char *msg) {
    perror(msg);
    exit(1);
}

static const char *ENTRY_PROBE =
    "syscall:::entry /pid == $target/ { "
    " self->d = self->d + 1; "
    " printf(\"%Y %*s-> %s [ucaller=%p]\\n\", walltimestamp, self->d*2, \"\", probefunc, ucaller); "
    " }";

static const char *RET_PROBE =
    "syscall:::return /pid == $target/ { "
    " printf(\"%Y %*s<- %s [ret=%d errno=%d]\\n\", walltimestamp, self->d*2, \"\", probefunc, rval0, errno); "
    " self->d = self->d - 1; "
    " }";

static pid_t spawn_dtrace_attach(pid_t target_pid) {
    char pidbuf[32];
    snprintf(pidbuf, sizeof(pidbuf), "%d", (int)target_pid);

    char *argv[] = {
        (char *)"dtrace",
        (char *)"-q",
        (char *)"-p", pidbuf,
        (char *)"-n", (char *)ENTRY_PROBE,
        (char *)"-n", (char *)RET_PROBE,
        NULL
    };

    pid_t dpid = 0;
    int rc = posix_spawnp(&dpid, "dtrace", NULL, NULL, argv, environ);
    if (rc != 0) { errno = rc; die("posix_spawnp(dtrace -p)"); }
    return dpid;
}

// Simple shell-escaped single-quoted token append
static void append_quoted(char **buf, size_t *cap, size_t *len, const char *s) {
    size_t need = strlen(s) * 6 + 3; // worst-case for '\'' expansion
    if (*len + need + 1 > *cap) {
        size_t ncap = (*cap ? *cap : 256);
        while (*len + need + 1 > ncap) ncap *= 2;
        char *nb = (char *)realloc(*buf, ncap);
        if (!nb) { free(*buf); die("realloc"); }
        *buf = nb; *cap = ncap;
    }
    (*buf)[(*len)++] = '\'';
    for (const char *p = s; *p; ++p) {
        if (*p == '\'') {
            memcpy(*buf + *len, "'\"'\"'", 6);
            *len += 6;
        } else {
            (*buf)[(*len)++] = *p;
        }
    }
    (*buf)[(*len)++] = '\'';
}

static char *join_as_shell_command(char *const *argv) {
    char *buf = NULL; size_t cap = 0, len = 0;
    for (int i = 0; argv[i]; i++) {
        if (i) { // space
            if (len + 1 >= cap) { cap = cap ? cap*2 : 256; buf = (char*)realloc(buf, cap); if(!buf) die("realloc"); }
            buf[len++] = ' ';
        }
        append_quoted(&buf, &cap, &len, argv[i]);
    }
    if (len + 1 >= cap) { cap = cap ? cap*2 : 256; buf = (char*)realloc(buf, cap); if(!buf) die("realloc"); }
    buf[len] = '\0';
    return buf;
}

static pid_t spawn_dtrace_exec(char *const *cmd_argv) {
    char *cmd = join_as_shell_command(cmd_argv);

    char *argv[] = {
        (char *)"dtrace",
        (char *)"-q",
        (char *)"-n", (char *)ENTRY_PROBE,
        (char *)"-n", (char *)RET_PROBE,
        (char *)"-c", cmd, // executed via /bin/sh -c internally
        NULL
    };

    pid_t dpid = 0;
    int rc = posix_spawnp(&dpid, "dtrace", NULL, NULL, argv, environ);
    free(cmd);
    if (rc != 0) { errno = rc; die("posix_spawnp(dtrace -c)"); }
    return dpid;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: sudo %s [-p pid] <program> [args...]\n", argv[0]);
        return 2;
    }

    // Attach to an existing PID
    if (strcmp(argv[1], "-p") == 0) {
        if (argc < 3) { fprintf(stderr, "-p requires a pid\n"); return 2; }
        int pid = atoi(argv[2]);
        if (pid <= 0) { fprintf(stderr, "invalid pid: %s\n", argv[2]); return 2; }
        pid_t dpid = spawn_dtrace_attach((pid_t)pid);
        int status = 0;
        if (waitpid(dpid, &status, 0) < 0) die("waitpid(dtrace)");
        return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
    }

    // Launch the target via DTrace (-c) to avoid attach races/SIP limitations
    pid_t dpid = spawn_dtrace_exec(&argv[1]);
    int status = 0;
    if (waitpid(dpid, &status, 0) < 0) die("waitpid(dtrace)");
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}