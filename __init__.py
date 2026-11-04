"""Native Hermes registrations; importing the plugin performs no I/O."""

from pathlib import Path


def _tool_handler(name):
    def handle(args, **kwargs):
        from .service import handle_tool

        return handle_tool(name, args)

    return handle


def register(ctx):
    from .schemas import TOOL_SCHEMAS

    for name, schema in TOOL_SCHEMAS.items():
        ctx.register_tool(
            name=name,
            toolset="network_xray",
            schema=schema,
            handler=_tool_handler(name),
            check_fn=lambda: True,
        )
    from .cli import configure, run

    ctx.register_cli_command(
        name="network-xray",
        help="Compare read-only network evidence from two vantage points",
        setup_fn=configure,
        handler_fn=run,
    )
    ctx.register_skill(
        name="workflow",
        path=Path(__file__).parent / "skills" / "workflow" / "SKILL.md",
        description="Diagnose why the same URL behaves differently on two machines.",
    )
