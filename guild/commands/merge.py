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

import click

from guild import click_util
from . import runs_merge


@click.command()
@runs_merge.merge_params
@click.pass_context
@click_util.use_args
@click_util.render_doc
def merge(ctx, args):
    """{{ runs_merge.merge_runs }}"""

    from . import merge_impl

    merge_impl.main(args, ctx)
