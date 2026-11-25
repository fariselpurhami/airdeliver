#!/usr/bin/env python3
"""Run dev Compose, hiding only its known stale-volume-label warning.

No volume metadata/data changes. Everything else is passed through, including
exit status and other warnings. Use --show-stale-volume-warnings to see all.
"""
import re
import subprocess
import sys

# Only project-local volume mismatch warnings, never data-loss prompts or errors.
STALE_VOLUME = re.compile(
    r'^(?:time="[^"]+" level=warning msg=")?'
    r'volume [\\"]+(airdeliver_dev_[A-Za-z0-9_.-]+)[\\"]+ carries the compose label '
    r'[\\"]+[^"\\]+[\\"]+ but does not match the compose file \(using '
    r'[\\"]+[^"\\]+[\\"]+\); it is left untouched .+ remove it manually if it is no longer needed"?$'
)


def is_stale_volume_warning(line):
    return bool(STALE_VOLUME.fullmatch(line.rstrip('\r\n')))


def run(args, *, executable=('docker','compose')):
    args=list(args)
    show='--show-stale-volume-warnings' in args
    if show:args.remove('--show-stale-volume-warnings')
    command=[*executable,'--env-file','.env.dev','-f','docker-compose.yml',
             '-f','docker-compose.dev.yml','-p','airdeliver_dev',*args]
    child=subprocess.Popen(command,stderr=subprocess.PIPE,text=True,bufsize=1)
    try:
        for line in child.stderr:
            if show or not is_stale_volume_warning(line):
                sys.stderr.write(line);sys.stderr.flush()
        return child.wait()
    except KeyboardInterrupt:
        # Normal terminal group signals reach Compose too. Preserve failure,
        # never retry or transform into a second potentially mutating command.
        return 130
    finally:
        child.stderr.close()


if __name__=='__main__':
    sys.exit(run(sys.argv[1:]))
