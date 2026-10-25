"""Injects lambda/*.py into cloudformation/template.base.yaml -> cloudformation/template.yaml
so one self-contained template deploys from the CLI or the CloudFormation console."""
import pathlib, re
root = pathlib.Path(__file__).parent
out = []
for line in (root / "cloudformation/template.base.yaml").read_text().splitlines():
    m = re.fullmatch(r"\s*__CODE:(\w+)__", line)
    if m:
        src = (root / "lambda" / f"{m.group(1)}.py").read_text()
        assert len(src) < 4096, f"{m.group(1)}.py is over the 4096-character inline limit"
        pad = " " * (len(line) - len(line.lstrip()))
        out += [pad + l if l else "" for l in src.splitlines()]
    else:
        out.append(line)
(root / "cloudformation/template.yaml").write_text("\n".join(out) + "\n")
print("Built cloudformation/template.yaml")
