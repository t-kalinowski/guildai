import os
import os.path
import json
import subprocess


from guild import config
from guild import guildfile
from guild import model as modellib
from guild import plugin as pluginlib
from guild import util
from guild import cli


class RScriptModelProxy:
    name = ""
    fullname = ""
    output_scalars = None
    objective = "loss"
    plugins = []

    def __init__(self, script_path, op_name):
        assert script_path[-2:].upper() == ".R", script_path
        assert script_path.endswith(op_name), (script_path, op_name)
        self.script_path = script_path
        if os.path.isabs(op_name) or op_name.startswith(".."):
            self.op_name = os.path.basename(op_name)
        else:
            self.op_name = op_name
        script_base = script_path[: -len(self.op_name)]
        self.reference = modellib.script_model_ref(self.name, script_base)
        self.modeldef = self._init_modeldef()

    def _init_modeldef(self):

        flags_data = infer_global_flags(self.script_path)
        data = [
            {
                "model": self.name,
                "operations": {
                    self.op_name: {
                        "exec": """Rscript -e 'guild.ai:::do_guild_run("%s")' ${flag_args}"""
                        % (os.path.relpath(self.script_path)),
                        "flags-dest": 'globals',
                        "flags": flags_data,
                        # "output-scalars": self.output_scalars,
                        # "objective": self.objective,
                        # "plugins": self.plugins,
                        "sourcecode": {
                            "dest": ".",
                            "select": [
                                {"exclude": {"dir": "renv"}},
                                {
                                    "include": {
                                        "text": [
                                            "renv.lock",
                                            ".Rprofile",
                                            ".Renviron",
                                            "**.[rR]",
                                        ]
                                    }
                                },
                            ],
                        },
                    }
                },
            }
        ]
        gf = guildfile.Guildfile(data, dir=os.path.dirname(self.script_path))
        return gf.models[self.name]


class RScriptPlugin(pluginlib.Plugin):

    resolve_model_op_priority = 60
    # share priority level with python_script, 60
    # must be less than exec_script level of 100

    def resolve_model_op(self, opspec):
        # pylint: disable=unused-argument,no-self-use
        """Return a tuple of model, op_name for opspec.

        If opspec cannot be resolved to a model, the function should
        return None.
        """
        if opspec.startswith(("/", "./")) and os.path.isfile(opspec):
            path = opspec
        else:
            path = os.path.join(config.cwd(), opspec)
        if is_r_script(path):
            model = RScriptModelProxy(path, opspec)
            return model, model.op_name
        return None


def normalize_path(x):
    x = os.path.expanduser(x)
    x = os.path.abspath(x)
    return x


def infer_global_flags(r_script_path):
    out = run_r("guild.ai:::infer_and_emit_global_flags('%s')" % r_script_path)
    return json.loads(out)


def is_r_script(opspec):
    return os.path.isfile(opspec) and opspec[-2:].upper() == ".R"


def check_guild_r_package_installled():
    installed = run_r('cat(requireNamespace("guild.ai", quietly = TRUE))') == "TRUE"
    if installed:
        return

    # TODO, consider vendoring r-pkg as part of pip pkg, auto-bootstrap R install
    # into a stand-alone lib we inject via prefixing R_LIBS env var
    consent = cli.confirm(
        "The 'guild.ai' R package must be installed in the R library. Continue?", True
    )
    if consent:
        run_r(
            'utils::install.packages("guild.ai", repos = c(CRAN = "https://cran.rstudio.com/"))'
        )
        return
    raise ImportError


def run_r(
    *exprs, file=None, infile=None, vanilla=True, default_packages='base', **run_kwargs
):
    assert (
        sum(map(bool, [exprs, file, infile])) == 1
    ), "exprs, file, and infile, are mutually exclusive. Only supply one."

    cmd = ["Rscript"]
    if default_packages:
        cmd.append("--default-packages=%s" % default_packages)
    if vanilla:
        cmd.append("--vanilla")

    if file:
        cmd.append(file)
    elif exprs:
        for e in exprs:
            cmd.extend(["-e", e])
    elif infile:
        cmd.append("-")
        run_kwargs['input'] = infile.encode()

    run_kwargs.setdefault("stderr", subprocess.STDOUT)
    run_kwargs.setdefault("stdout", subprocess.PIPE)
    run_kwargs.setdefault("check", True)

    out = subprocess.run(cmd, **run_kwargs)
    return out.stdout.decode()
