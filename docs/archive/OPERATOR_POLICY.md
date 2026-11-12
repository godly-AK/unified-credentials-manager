# Lab operator recovery policy

This is the proposed procedure for UCM's database-operator commands. The command mechanics were rehearsed with a synthetic account on November 3, 2026: node inventory, node revocation, lost-phone recovery, two high-risk audit events, and invalidation of the former bearer session all passed. The **human identity check** below has not been exercised with a real student or organization.

## Who may act

Only a designated lab operator with access to the UCM database environment may run the commands. UCM exposes no public operator reset endpoint. Do not give ordinary website accounts database credentials. Record the operator's name, a case identifier, the person approving the action, and the reason in a restricted lab record. A shared workstation account is not sufficient as an operator identity by itself.

## Lost main phone

1. The account owner reports the loss through a channel already known to the lab. Do not treat a message from the potentially compromised UCM account as the sole proof.
2. Meet the owner in person, compare a campus identity card with the enrollment record, and have a second designated operator or instructor approve the reset. If the owner cannot attend, defer the action until an equivalent documented independent identity procedure is approved.
3. Back up the database and confirm the target username and current enrolled-phone status. Record the case identifier, both operator names, time, and reason.
4. Run the [lost-phone recovery command](TRUST_LEVELS.md#operator-recovery-for-a-lost-main-phone). Include the case identifier and operator names in the `--reason` text. Type the username confirmation carefully.
5. Confirm the prior phone key and all sessions are invalid, the high-risk `DEVICE_OPERATOR_RESET` event exists, and the owner can sign in with the existing password and enroll a new phone. Ask the owner to change the password if compromise is suspected.

## Lost workplace node

1. Confirm which slot and node ID are affected. Use the [operator inventory command](TRUST_LEVELS.md#operator-response-to-a-lost-workplace-node) rather than guessing from a label.
2. Verify the report with the account owner or designated workplace custodian and record a case identifier and operator identity.
3. Run the operator revoke command with the exact node ID and a reason containing the case identifier. Confirm the `WORKPLACE_NODE_OPERATOR_REVOKED` event is high risk, the node is revoked, and office access and pending approvals are invalid.
4. Supervise enrollment of a replacement physical phone. Do not reuse the lost phone's key or an old enrollment code.

## What this policy does not prove

The emergency CLI relies on database-host access; it does not implement two-person cryptographic approval or a web reset endpoint. A separate [administrator monitoring role](ADMIN_MONITORING.md) allows approved users to read and review events after main-phone and two-node office approval, but it does **not** grant access to these emergency commands. The reason field is free text, so a real organization should attach it to its case-management records and audit database access separately. This policy is a lab operating procedure until the designated people and identity records are established.

For monitoring-role grants and removal, verify the proposed administrator's identity and assignment, record a case identifier and approving operator, then use the confirmed `app.admin.roles` command in the [monitoring guide](ADMIN_MONITORING.md). Remove the role when the assignment ends and verify the account's old session stops working. Do not promote a generic shared account.
