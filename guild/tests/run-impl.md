# Run impl tests

    >>> def run(cwd=".", **kw):
    ...     from guild import click_util
    ...     from guild.commands import run, run_impl2
    ...     ctx = run.run.make_context("", [])
    ...     ctx.params.update(kw)
    ...     args = click_util.Args(**ctx.params)
    ...     with SetCwd(cwd):
    ...         try:
    ...             run_impl2.main(args)
    ...         except SystemExit as e:
    ...             print(e.args[0])
    ...             print("<exit %i>" % e.args[1] if len(e.args) > 1 else 1)

    >>> def init_gf(s):
    ...     cwd = mkdtemp()
    ...     write(path(cwd, "guild.yml"), s)
    ...     return cwd

## Invalid arg combinations

    >>> run(opspec="foo", start="bar")
    OPERATION cannot be used with --start
    Try 'guild run --help' for more information.
    <exit 1>

    >>> run(opspec="foo", restart="bar")
    OPERATION cannot be used with --restart
    Try 'guild run --help' for more information.
    <exit 1>

## Invalid restart and start specs

    >>> guild_home = mkdtemp()

    >>> with SetGuildHome(guild_home):
    ...     run(restart="foo")
    could not find a run matching 'foo'
    Try 'guild runs list' for a list.
    <exit 1>

    >>> with SetGuildHome(guild_home):
    ...     run(start="bar")
    could not find a run matching 'bar'
    Try 'guild runs list' for a list.
    <exit 1>

## Invalid cwd Guild file

    >>> cwd = init_gf("invalid_guildfile_contents")
    >>> with LogCapture(stdout=True):
    ...     run(cwd)
    ERROR: error in ...guild.yml: invalid guildfile data
    'invalid_guildfile_contents': expected a mapping
    guildfile in '...' contains an error (see above for details)
    <exit 1>

## Invalid op spec

    >>> run(opspec="a/a/a")
    invalid operation spec 'a/a/a'
    Try 'guild operations' for a list of available operations.
    <exit 1>

## No matching model or operation

    >>> cwd = init_gf("""
    ... - model: foo1
    ... - model: foo2
    ... """)

No default operation:

    >>> run(cwd)
    cannot find a default operation
    Try 'guild operations' for a list.
    <exit 1>

Can't find operation - no model spec):

    >>> run(cwd, opspec="foo")
    cannot find operation foo
    You may need to include a model in the form MODEL:OPERATION. Try
    'guild operations' for a list of available operations.
    <exit 1>

Can't find operation - model spec but no such model:

    >>> run(cwd, opspec="bar:foo")
    cannot find operation bar:foo
    Try 'guild operations' for a list of available operations.
    <exit 1>

Can't find operation - matched model but no such op:

    >>> run(cwd, opspec="foo1:bar")
    operation 'bar' is not defined for model 'foo1'
    Try 'guild operations foo1' for a list of available operations.
    <exit 1>

Multiple matching models:

    >>> run(cwd, opspec="foo:bar")
    there are multiple models that match 'foo'
    Try specifying one of the following:
      foo1
      foo2
    <exit 1>

Anonymous model:

    >>> cwd = init_gf("{}")

    >>> run(cwd, opspec="foo")
    operation 'foo' is not defined
    Try 'guild operations' for a list of available operations.
    <exit 1>

## Invalid main flag reference

    >>> cwd = init_gf("""
    ... op:
    ...   main: guild.pass ${foo}
    ... """)
    >>> run(cwd, opspec="op")
    invalid setting for operation 'op': main contains invalid reference 'foo'
    <exit 1>

## Invalid flag arg

    >>> cwd = init_gf("op: { exec: 'true' }")
    >>> run(cwd, opspec="op", flags=["foo"])
    invalid argument 'foo' - expected NAME=VAL
    <exit 1>

## Model and op help

    >>> cwd = init_gf("""
    ... - model: m1
    ...   description: A sample model
    ...   operations:
    ...     op1:
    ...       description: Some op 1
    ...       exec: 'true'
    ...       flags:
    ...         foo: 1
    ...         bar:
    ...           description: Some flag bar
    ...           default: B
    ... """)

    >>> run(cwd, help_model=True)
    Usage: guild run [OPTIONS] m1:OPERATION [FLAG]...
    <BLANKLINE>
    A sample model
    <BLANKLINE>
    Use 'guild run m1:OPERATION --help-op' for help on a particular operation.
    <BLANKLINE>
    Operations:
      op1  Some op 1

    >>> run(cwd, help_op=True)
    Usage: guild run [OPTIONS] m1:op1 [FLAG]...
    <BLANKLINE>
    Some op 1
    <BLANKLINE>
    Use 'guild run --help' for a list of options.
    <BLANKLINE>
    Flags:
      bar  Some flag bar (default is B)
      foo  (default is 1)

## Test output scalars

Sample Guild file with various output scalar patterns:

    >>> cwd = init_gf("""
    ... op1: { main: guild.pass }
    ... op2:
    ...   main: guild.pass
    ...   output-scalars:
    ...     foo: ' - foo=(\\value)'
    ...     bar: 'bar is (\\value)'
    ... op3:
    ...   main: guild.pass
    ...   output-scalars:
    ...     - '(\\key) is (\\value)'
    ...     - step: 'Epoch: (\\step)'
    ... """)

Sample output:

    >>> out = path(cwd, "out.txt")
    >>> write(out, """line-1
    ... a: 1.123
    ... b: 2
    ... Epoch: 10
    ... foo is 4.432
    ... bar is 3.321
    ... line-2
    ...  - foo=1
    ...  - bar=2
    ... """)

Output scalar test - op1:

    >>> run(cwd, opspec="op1", test_output_scalars=out)
    line-1
      '^([^ \t]+):\\s+([0-9\\.e\\-]+)$': <no matches>
    a: 1.123
      '^([^ \t]+):\\s+([0-9\\.e\\-]+)$': [('a', '1.123')] (a=1.123)
    b: 2
      '^([^ \t]+):\\s+([0-9\\.e\\-]+)$': [('b', '2')] (b=2.0)
    Epoch: 10
      '^([^ \t]+):\\s+([0-9\\.e\\-]+)$': [('Epoch', '10')] (Epoch=10.0)
    foo is 4.432
      '^([^ \t]+):\\s+([0-9\\.e\\-]+)$': <no matches>
    bar is 3.321
      '^([^ \t]+):\\s+([0-9\\.e\\-]+)$': <no matches>
    line-2
      '^([^ \t]+):\\s+([0-9\\.e\\-]+)$': <no matches>
     - foo=1
      '^([^ \t]+):\\s+([0-9\\.e\\-]+)$': <no matches>
     - bar=2
      '^([^ \t]+):\\s+([0-9\\.e\\-]+)$': <no matches>

Output scalar test - op2:

    >>> run(cwd, opspec="op2", test_output_scalars=out)
    line-1
      'bar is ([0-9\\.e\\-]+)': <no matches>
      ' - foo=([0-9\\.e\\-]+)': <no matches>
    a: 1.123
      'bar is ([0-9\\.e\\-]+)': <no matches>
      ' - foo=([0-9\\.e\\-]+)': <no matches>
    b: 2
      'bar is ([0-9\\.e\\-]+)': <no matches>
      ' - foo=([0-9\\.e\\-]+)': <no matches>
    Epoch: 10
      'bar is ([0-9\\.e\\-]+)': <no matches>
      ' - foo=([0-9\\.e\\-]+)': <no matches>
    foo is 4.432
      'bar is ([0-9\\.e\\-]+)': <no matches>
      ' - foo=([0-9\\.e\\-]+)': <no matches>
    bar is 3.321
      'bar is ([0-9\\.e\\-]+)': [('3.321',)] (bar=3.321)
      ' - foo=([0-9\\.e\\-]+)': <no matches>
    line-2
      'bar is ([0-9\\.e\\-]+)': <no matches>
      ' - foo=([0-9\\.e\\-]+)': <no matches>
     - foo=1
      'bar is ([0-9\\.e\\-]+)': <no matches>
      ' - foo=([0-9\\.e\\-]+)': [('1',)] (foo=1.0)
     - bar=2
      'bar is ([0-9\\.e\\-]+)': <no matches>
      ' - foo=([0-9\\.e\\-]+)': <no matches>

Output scalar test - op3:

    >>> run(cwd, opspec="op3", test_output_scalars=out)
    line-1
      '([^ \t]+) is ([0-9\\.e\\-]+)': <no matches>
      'Epoch: ([0-9]+)': <no matches>
    a: 1.123
      '([^ \t]+) is ([0-9\\.e\\-]+)': <no matches>
      'Epoch: ([0-9]+)': <no matches>
    b: 2
      '([^ \t]+) is ([0-9\\.e\\-]+)': <no matches>
      'Epoch: ([0-9]+)': <no matches>
    Epoch: 10
      '([^ \t]+) is ([0-9\\.e\\-]+)': <no matches>
      'Epoch: ([0-9]+)': [('10',)] (step=10.0)
    foo is 4.432
      '([^ \t]+) is ([0-9\\.e\\-]+)': [('foo', '4.432')] (foo=4.432)
      'Epoch: ([0-9]+)': <no matches>
    bar is 3.321
      '([^ \t]+) is ([0-9\\.e\\-]+)': [('bar', '3.321')] (bar=3.321)
      'Epoch: ([0-9]+)': <no matches>
    line-2
      '([^ \t]+) is ([0-9\\.e\\-]+)': <no matches>
      'Epoch: ([0-9]+)': <no matches>
     - foo=1
      '([^ \t]+) is ([0-9\\.e\\-]+)': <no matches>
      'Epoch: ([0-9]+)': <no matches>
     - bar=2
      '([^ \t]+) is ([0-9\\.e\\-]+)': <no matches>
      'Epoch: ([0-9]+)': <no matches>

## Print command

    >>> cwd = init_gf("""
    ... default:
    ...   main: guild.pass
    ...
    ... with-args:
    ...   main: guild.pass --foo --bar=123
    ...
    ... with-flags:
    ...   main: guild.pass
    ...   flags:
    ...     s: S
    ...     i: 123
    ...     f: 1.123
    ...     b: no
    ...     n:
    ...       arg-name: N
    ...     w:
    ...       arg-switch: true
    ... """)

    >>> run(cwd, opspec="default", print_cmd=True)
    ??? -um guild.op_main guild.pass --

    >>> run(cwd, opspec="with-args", print_cmd=True)
    /usr/bin/python -um guild.op_main guild.pass --foo --bar=123 --

    >>> run(cwd, opspec="with-flags", print_cmd=True)
    /usr/bin/python -um guild.op_main guild.pass -- --b no --f 1.123 --i 123 --s S

    >>> run(cwd, opspec="with-flags",
    ...     flags=["b=yes", "i=456", "w=true", "s=T", "n=hello"],
    ...     print_cmd=True)
    ??? -um guild.op_main guild.pass -- --N hello --b yes --f 1.123 --i 456 --s T --w

## Pre-proc

    >> cwd = init_gf("""
    ... op:
    ...   pre-process: echo hello
    ...   main: guild.pass
    ... """)

    >> run(cwd, opspec="op", yes=True)


## == TODO =====================================================

- [ ] Run script

- [ ] Run opdef
  - [ ] Default op
  - [ ] Named op, no modelspec
  - [ ] Model + op Guildfile
  - [ ] Just op package
  - [ ] Model + op package
  - [ ] Built-ins

- [ ] Restart run - can find opdef
  - [ ] No flag changes
  - [ ] Flag changes

- [ ] Restart run - can't find opdef
  - [ ] No flag changes
  - [ ] Flag changes (expect error)

- [ ] Flag args
  - [ ] Normal
  - [ ] Include batch files
  - [ ] Invalid

- [ ] Print env
- [ ] Print trials
- [ ] Save trials