# Lab 5: Watch the whole chain run

**Time:** 20 minutes
**You start with:** the webhook, connector, workflow, and rule from [Lab 4](lab-04-webhook.md).
**You finish with:** a failure that triages itself, with no human in the loop between the break and
the findings.

## 1. Clear the decks

Two things stop a new case from being created, and both are easy to miss:

- **An open case.** The rule adds alerts to an open case for 7 days instead of opening a new one.
  In Kibana, open **Observability** > **Cases** and close any case from earlier labs.
- **A disabled rule.** In **Observability** > **Alerts** > **Manage rules**, enable
  `payment-service error spike` again.

## 2. Run the scenario

`scenario.sh` restarts both hosts, runs healthy traffic, and then breaks host-a. It stays in the
foreground, so start it in a second terminal:

```bash
HEALTHY_MIN=5 FAULT_MIN=15 ./scripts/scenario.sh
```

`HEALTHY_MIN` and `FAULT_MIN` set each phase in minutes. The healthy phase matters: it gives you a
baseline to compare against, and it proves the rule is quiet when the service is well.

The script prints the exact time it injects the fault. Note it down; every measurement below is
relative to that moment.

## 3. Follow it

About a minute after `FAULT injected` appears, run this in your first terminal:

```bash
./scripts/check-chain.sh
```

Then watch each hop:

| Where | What you should see |
|---|---|
| Kibana > **Observability** > **Alerts** | `payment-service error spike` active |
| Kibana > **Observability** > **Cases** | A new `high` severity case, `payment-service error spike (...) (Auto-created)` |
| Kibana > **Workflows** > **Executions** | A run with all seven steps completed |
| The case | A comment starting `Forwarded to AWS DevOps Agent` |
| Operator web app > **Incidents** | A HIGH priority incident, **Triggered By: Event Channel** |

Our run, with nobody touching anything after the script started:

| Time (UTC) | What happened | Since the failure |
|---|---|---|
| 22:56:45 | `scenario.sh` breaks host-a's connection pool | 0 s |
| 22:57:20 | The rule opens a high-severity case | 35 s |
| 22:57:25 | The workflow runs and writes the audit record | 40 s |
| 22:57:27 | AWS DevOps Agent creates a HIGH priority incident | 42 s |
| 22:57:41 | The investigation starts | 56 s |
| 23:01:49 | The investigation completes | about 5 min |

If an investigation of the same problem is still open when a new incident arrives, AWS DevOps Agent
links the new one to it (status **Linked**) rather than starting again.

## 4. Read the findings

Open the incident in the operator web app. The summary tabs hold the incident description, the
investigation timeline with every Elastic query, the root cause, the mitigation plan, and a review
page.

Our investigation used 7 of its 12 Elastic tools with no errors, `platform_core_execute_esql` most
often, and reported:

- About 77% of payments on host-a failed after waiting the full 2 seconds for a database
  connection. Host-b had no errors and answered in about 31 ms.
- Each query held a connection for about 1.5 seconds. With 2 connections, host-a could serve about
  1.3 payments per second while about 5.9 were arriving.
- Thread counts and in-flight requests were rising, which points to queueing rather than extra load.
- **Root cause, marked Confirmed:** a call to `/admin/fault` switched host-a into
  `pool_exhaustion` mode at a named time. It also noticed the same fault had run earlier in the day.
- **Mitigation plan, marked for review:** restore the pool settings, then require authentication on
  `/admin/fault` and alert on `fault mode changed`.

## 5. Compare with Lab 3

Put this investigation next to the one you ran by hand in Lab 3. Same failure, same data, better
answer:

| | Lab 3 (chat) | Lab 5 (alert-driven) |
|---|---|---|
| Found the failing host | Yes | Yes |
| Named the error | Yes | Yes |
| Found when it started | No | Yes |
| Named the configuration change | No | Yes |
| Explained capacity vs demand | No | Yes |
| Produced a mitigation plan | Next step only | Full plan, marked for review |

The difference is the evidence the workflow put in the incident description. The agent started from
numbers instead of starting from scratch.

One gap remains in both runs: no host-level CPU and memory, because the sample sends process
metrics only. Adding the OpenTelemetry host metrics receiver closes it.

## 6. Reset

The fault stays on after the scenario ends:

```bash
./scripts/run-local.sh heal
```

## Check your work

- A case you did not create exists, opened by the rule.
- An incident you did not create exists, with **Triggered By: Event Channel**.
- The investigation named the host and the connection pool.
- You can state the time from failure to findings for your own run.

## Troubleshooting

| What you see | What to check |
|---|---|
| No new case appears | An earlier case is still open, or the rule is still disabled |
| The rule is active but no case appears | The rule's Cases action is missing. Re-run `./scripts/06-setup-elastic-alerting.sh` |
| The case is `low` severity | The case template did not apply. Re-run the setup script and check `elastic-config/rules/cases-configure.json` |
| The incident shows **Linked** | An investigation of the same problem is still open. Wait for it to finish, then run the scenario again |
| The investigation finds no Elastic data | Telemetry stopped. Check `./scripts/run-local.sh status` |

**Next:** [Lab 6: Clean up](lab-06-cleanup.md)
