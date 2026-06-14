# Migration Plan

Step one inventories source memory. Step two builds the migration adapter and
maps each source memory packet into a hydration packet. Step three runs the
validation gate against every decision record.

The validation gate checks that stale-state markers are preserved, rollback
notes name the failed packet, and operator approval is recorded before durable
state is written.
