"""Command-line interface: argparse wrapper.

Exposes --source, --size, --debug. Parsed before QApplication construction
where possible so a bad flag exits before any Qt state is created.
"""
