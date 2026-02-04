

**Current code:**
```painless
def total_impact = host.top_hits.hits.hits.0._source.labels.alert.impact.total_impact;
if (total_impact >= 1000 && total_impact < 5000) {
  ticket_priority = '2 - High';
} else if (total_impact >= 5000) {
  ticket_priority = '1 - Critical';
}
```

**Updated code:**
```painless
def total_impact = host.top_hits.hits.hits.0._source.labels.alert.impact.total_impact;
if (total_impact >= 750 && total_impact < 2500) {
  ticket_priority = '2 - High';
} else if (total_impact >= 2500) {
  ticket_priority = '1 - Critical';
}
```

**Summary of changes:**
- P1 (Critical): Changed from `>= 5000` to `>= 2500`
- P2 (High): Changed from `>= 1000 && < 5000` to `>= 750 && < 2500`
- P3 (Moderate): Remains the default, now applies when `< 750` (previously `< 1000`)

No other changes were made.
