# Facilitator notes

For running the labs as a guided workshop. Read this before the session.

## Timing

Two hours including a break, for a group that is comfortable at a terminal.

| Segment | Time | Notes |
|---|---|---|
| Intro: the problem and the architecture | 15 min | Use the two diagrams: telemetry into Elastic, then the alert-to-investigation flow |
| Lab 0: setup | 20 min | The slowest step. Ask participants to do it beforehand if you can |
| Lab 1: telemetry | 15 min | Everyone should see data in Kibana before you move on |
| Lab 2: MCP | 20 min | Pause on the two-control idea: read-only key plus tool allowlist |
| Lab 3: investigate | 20 min | Inject the fault, then talk through the gaps while the agent works |
| Break | 10 min | Good place to let a scenario run |
| Lab 4: webhook and workflow | 25 min | Walk the workflow YAML on screen |
| Lab 5: end to end | 20 min | The payoff. Have everyone call out their own timings |
| Debrief and Lab 6 | 15 min | Confirm every participant's teardown finished |

## Before the session

Send participants the prerequisites from [Lab 0](lab-00-setup.md) a few days ahead, and ask them to
confirm two commands succeed:

```bash
aws sts get-caller-identity
aws cloudformation describe-type --region <region> \
  --type RESOURCE --type-name AWS::DevOpsAgent::AgentSpace --query TypeName --output text
```

The second one catches the most common blocker: AWS DevOps Agent not being available or permitted
in their account or Region. Some organizations restrict which accounts may register third-party MCP
servers, and that restriction surfaces as `AccessDenied` on `AWS::DevOpsAgent::Service` in Lab 2.
Have participants check with their account administrator in advance.

Also confirm their Elastic project is Serverless Observability on the **Complete** tier. If
**Workflows** is missing from the Kibana menu, Labs 4 and 5 cannot run.

## Shared versus per-participant resources

| Resource | Recommendation |
|---|---|
| AWS account | One sandbox account per participant is cleanest. In a shared account, set a unique `STACK_NAME` and `MCP_STACK_NAME` per person, because IAM role names are global |
| Elastic project | One per participant. On a shared project, Kibana object names collide: the connector, workflow, rule, and case template are created by fixed ID |
| Agent Space | One per participant. An Agent Space allows only one API key webhook |

If you must share an Elastic project, have participants use separate Kibana spaces and adjust the
object names in `elastic/` and the MCP path (`/s/<space>/api/agent_builder/mcp`).

## Cost

AWS DevOps Agent bills per agent-second of active work. Each participant runs two investigations of
5 to 8 minutes, plus some chat. Elastic Cloud Serverless bills for ingest and retention; the sample
sends 12 requests per second per participant. CloudFormation and IAM are free. Check current rates
at [AWS DevOps Agent pricing](https://aws.amazon.com/devops-agent/pricing/) and
[Elastic Cloud Serverless pricing](https://www.elastic.co/pricing), and tell participants what they
are spending before Lab 3.

**Budget your own time too.** Idle services keep sending telemetry. Lab 6 is not optional.

## Teaching moments worth pausing on

**Lab 2, two controls not one.** Ask why both the read-only key and the tool allowlist are needed.
The answer: Elastic lists all 54 tools whatever the key allows, so the allowlist is what keeps the
agent from calling write tools, and the key is what makes a mistake harmless.

**Lab 3, the gaps.** Resist fixing them. The gaps are the argument for the next lab and for custom
Agent Builder tools. Let participants see an agent exploring unfamiliar data.

**Lab 4, the silent failure.** The webhook returns HTTP 200 for an invalid `priority` or `action`
and no investigation starts. This is the single most confusing failure in the whole workshop. Show
the audit index before anyone hits it.

**Lab 5, the comparison.** Have participants read their Lab 5 findings next to their Lab 3 answer.
The difference is evidence in the incident description, not a better model.

## Failure modes, in the order you will hit them

| Symptom | Cause | Fix |
|---|---|---|
| `syntax error near unexpected token` | Angle brackets left in `.env` | Replace with real values |
| Creating the read-only key fails | Request ran with an API key, not a signed-in user | Use Kibana Dev Tools as a user |
| `AccessDenied` on `AWS::DevOpsAgent::Service` | Account not permitted to register third-party MCP servers | Account administrator. Participants can still do Labs 1, 4, and part of 5 |
| Role name already exists | Two stacks in one account using the same name | Unique `STACK_NAME` per participant |
| No data in Elastic | Wrong `OTLP_ENDPOINT` or `OTLP_API_KEY` | Check `.run/payments-host-a.log` |
| No new case on a repeat run | Open case from a previous lab | Close it; the rule groups for 7 days |
| Incident shows **Linked** | Investigation of the same problem still open | Wait, then re-run |
| Connector rejected: `authType must be null` | Copied config without `"authType": null` | Use the repo file as-is |

## If you are short on time

- Do the setup (Lab 0) as homework.
- Run Lab 3 as a demo on your screen rather than per participant; it is 10 minutes of waiting.
- Skip the manual case test in Lab 4 step 3 and go straight to Lab 5. You lose a checkpoint but
  save 10 minutes.

## If a participant is blocked on AWS

Labs 1, 4, and the Elastic half of Lab 5 work without AWS DevOps Agent. Pair them with someone
whose account works for Labs 2, 3, and 5, and have them drive the Elastic side.
