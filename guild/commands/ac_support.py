# Copyright 2017-2022 RStudio, PBC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import pathlib
import re
import subprocess

from guild.util import natsorted


def ac_filename(ext=None, incomplete=None):
    if os.getenv("_GUILD_COMPLETE"):
        if current_shell_supports_directives():
            return _compgen_filenames("file", ext)
        return _list_dir(os.getcwd(), incomplete, ext=ext)
    return []


def _list_dir(dir, incomplete, filters=None, ext=None):
    """Python based directory listing for completions.

    We use shell functions (e.g. compgen on bash) where possible to
    provide listing. This is for the sake of speed as well as making
    the behavior as close as possible to the user's native
    shell. However, supporting new shells means implementing behavior
    for our !! directives. We provide native Python implementation as
    a fallback where we have not yet implemented handling for our
    directives.
    """
    ext = _ensure_leading_dots(ext)
    if incomplete and os.path.sep in incomplete:
        leading_dir, incomplete = os.path.split(incomplete)
    else:
        leading_dir = ""
    fulldir = os.path.join(dir, leading_dir)

    if not os.path.isdir(fulldir):
        return []

    results = set()

    for path in pathlib.Path(fulldir).iterdir():
        key = str(path.relative_to(dir)) + ("/" if path.is_dir() else "")
        # pylint: disable=too-many-boolean-expressions
        if (
            (not ext or path.suffix in set(ext))
            and path.name not in {".guild", "__pycache__"}
            and (not incomplete or path.name.startswith(incomplete))
            and (not filters or all(filter(str(path)) for filter in filters))
        ):
            results.add(key)
    return natsorted(results)


def _ensure_leading_dots(l):
    if not l:
        return l
    return ["." + x if x[:1] != "." else x for x in l]


def ac_dir(incomplete=None):
    if os.getenv("_GUILD_COMPLETE"):
        if current_shell_supports_directives():
            return ["!!dir"]
        return _list_dir(os.getcwd(), incomplete, filters=[os.path.isdir])
    return []


def ac_opnames(names):
    if os.getenv("_GUILD_COMPLETE"):
        if current_shell_supports_directives():
            names = ["!!no-colon-wordbreak"] + names
        return names
    return []


def _compgen_filenames(type, ext):
    if not ext:
        return ["!!%s:*" % type]
    return ["!!%s:*.@(%s)" % (type, "|".join(ext))]


def ac_nospace():
    # TODO: zsh supports this directive, but not the others.
    # We should add proper support for all of them at some point.
    if (
        os.getenv("_GUILD_COMPLETE")
        and current_shell_supports_directives()
        or current_shell() == "zsh"
    ):
        return ["!!nospace"]
    return []


def ac_batchfile(ext=None, incomplete=None):
    incomplete = incomplete or ""
    if os.getenv("_GUILD_COMPLETE"):
        if current_shell_supports_directives():
            return _compgen_filenames("batchfile", ext)
        return [
            "@" + str(item)
            for item in _list_dir(os.getcwd(), incomplete.replace("@", ""), ext=ext)
        ]
    return []


def ac_command(filter=None, incomplete=None):
    if os.getenv("_GUILD_COMPLETE"):
        if current_shell_supports_directives():
            if filter:
                return ["!!command:%s" % filter]
            return ["!!command"]

        # TODO: how should we handle this on windows? call out to bash explicitly? better
        #    to avoid explicitly calling sh.
        available_commands = subprocess.check_output(
            [
                "sh",
                "-c",
                "ls $(echo $PATH | tr ':' ' ') | grep -v '/' | grep . | sort | uniq",
            ],
            stderr=subprocess.DEVNULL,
        )
        available_commands = [_.decode() for _ in available_commands.strip().split()]
        if filter:
            filter_re = re.compile(filter)
            available_commands = [
                cmd for cmd in available_commands if filter_re.match(cmd)
            ]
        if incomplete:
            available_commands = [
                cmd for cmd in available_commands if cmd.startswith(incomplete)
            ]
        return available_commands
    return []


def ac_run_dirpath(run_dir, all=False, incomplete=None):
    if os.getenv("_GUILD_COMPLETE"):
        if current_shell_supports_directives():
            if all:
                return ["!!allrundirs:%s" % run_dir]
            return ["!!rundirs:%s" % run_dir]
        filters = [os.path.isdir, lambda x: os.path.isdir(os.path.join(x, ".guild"))]
        if all:
            filters.pop()
        return _list_dir(dir=run_dir, incomplete=incomplete, filters=filters)
    return []


def ac_run_filepath(run_dir, incomplete):
    if os.getenv("_GUILD_COMPLETE"):
        if current_shell_supports_directives():
            return ["!!runfiles:%s" % run_dir]
        return _list_dir(run_dir, incomplete)
    return []


def ac_safe_apply(ctx, f, args):
    from guild import config

    with config.SetGuildHome(ctx.parent.params.get("guild_home")):
        try:
            return f(*args)
        except (Exception, SystemExit):
            if os.getenv("_GUILD_COMPLETE_DEBUG") == "1":
                raise
            return None


def current_shell():
    parent_shell = os.getenv("_GUILD_COMPLETE_SHELL")
    known_shells = {"bash", "zsh", "fish", "dash", "sh"}

    if not parent_shell:
        parent_shell = os.path.basename(psutil.Process().parent().exe())
    if parent_shell not in known_shells:
        # if we use something like make to launch guild, we may need
        # to look one level higher.
        parent_of_parent = os.path.basename(psutil.Process().parent().parent().exe())
        if parent_of_parent in known_shells:
            parent_shell = parent_of_parent
        else:
            log.warning("unknown shell '%s', assuming %s", parent_shell, DEFAULT_SHELL)
            parent_shell = DEFAULT_SHELL
    return parent_shell


def current_shell_supports_directives():
    # TODO: we should maybe register this support in a more dynamic
    # way instead of hard-coding it
    return current_shell() in {
        "bash",
    }
