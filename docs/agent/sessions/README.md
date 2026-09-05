# Session transcripts

One file per Claude Code session: `NN-<stage>-<topic>.md`. Excerpts are fine; keep the parts that show
(a) the prompt as given, (b) a place the agent asked/decided something, (c) the test/lint run it reported,
(d) anything it got wrong and the correction. Redact secrets.

Template:

```
# NN — <stage> — <topic>
Date / duration:
Prompt file: docs/agent/prompts/NN-*.md
Model/tool: Claude Code (<model>)

## Excerpt
<paste>

## Outcome
Commits:
What I changed by hand afterwards:
Mistakes caught:
```
