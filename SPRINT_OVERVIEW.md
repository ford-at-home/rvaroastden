# AI Roast Den: Sprint Overview & Quick Reference

## 🚨 Critical Path: Lambda → Fargate Migration

**THE PROBLEM**: Discord bots need persistent connections. Lambda times out after 15 minutes. The bot disconnects and dies. This blocks EVERYTHING.

**THE SOLUTION**: 
```
Discord ← WebSocket → Fargate Container (Always On)
                            ↓
                          SQS Queue
                            ↓
                    Lambda Functions (Process Messages)
```

## Sprint Timeline & Deliverables

### 🚨 Sprint 0: Emergency Fix (Week 1)
**Mission**: Fix the architecture or nothing else matters

| Day | Task | Deliverable |
|-----|------|-------------|
| Mon | Create Fargate container | Dockerfile with Discord.py |
| Tue | Set up SQS integration | Message queue flow working |
| Wed | Update CDK stack | Fargate deployment ready |
| Thu | Test persistent connection | 24-hour uptime proof |
| Fri | Deploy & validate | Working bot in Fargate |

**Demo**: "Look, the bot stays online all day!"

### 🤖 Sprint 1: Personalities (Week 2)
**Mission**: Make the bots actually interesting

| Component | Status | Files to Create |
|-----------|--------|-----------------|
| Personality System | ❌ | `/personalities/ford_bot.json` |
| Dynamic Loading | ❌ | `/utils/personality_loader.py` |
| Roast Logic | ❌ | `/handlers/roast_handler.py` |
| Commands | ❌ | Update `bot.py` |

**Demo**: "Ford roasts differently than Elise!"

### 🧠 Sprint 2: Memory (Week 3)
**Mission**: Bots that remember = bots that matter

- Short-term: Last 100 messages
- Long-term: Inside jokes, references
- Context: 10-message window
- Triggers: Personality-specific recalls

**Demo**: "Remember that time you said..."

### 🛡️ Sprint 3: Safety (Week 4)
**Mission**: Keep it fun, not toxic

- Rate limiting: 5 msg/user/min
- Roast cooldown: 30 seconds
- Content filters: AWS Comprehend
- Admin controls: !mute, !clear

**Demo**: "Spam all you want, bot stays cool"

### 👥 Sprint 4: Multi-Bot (Week 5)
**Mission**: Party mode with multiple personalities

- Bot registry system
- Inter-bot awareness
- Group dynamics
- No response loops

**Demo**: "5 bots roasting each other!"

### 🎮 Sprint 5: Higher Self (Week 6)
**Mission**: Humans influence their AI selves

- User → Bot mapping
- Real-time influence
- Behavior modification
- Audit trails

**Demo**: "I made my bot tell that joke!"

### 🚀 Sprint 6: Production (Week 7-8)
**Mission**: Ship it!

- Testing: 80% coverage
- Monitoring: Full dashboards
- Docs: Everything documented
- Optimization: $30-50/month

**Demo**: "100 users, still running smooth"

## Quick Decision Tree

```
Is the bot staying online?
├─ No → Sprint 0 (Fargate fix)
└─ Yes → Continue
   │
   Are personalities working?
   ├─ No → Sprint 1 
   └─ Yes → Continue
      │
      Does it remember conversations?
      ├─ No → Sprint 2
      └─ Yes → Continue
         │
         Is it safe for production?
         ├─ No → Sprint 3
         └─ Yes → Ship MVP!
```

## Cost Breakdown by Sprint

| Sprint | Dev Cost | AWS Cost | Total |
|--------|----------|----------|-------|
| 0 | Fix architecture | $20 | $20 |
| 1 | Basic features | $30 | $30 |
| 2 | Memory system | $40 | $40 |
| 3 | Safety features | $45 | $45 |
| 4 | Multi-bot | $60 | $60 |
| 5 | Advanced | $50 | $50 |
| 6 | Polish | $50 | $50 |

**Target**: $30-50/month in production

## Red Flags to Watch

1. **Fargate costs spiral** → Implement aggressive caching
2. **Claude API limits** → Add request queuing
3. **Memory explosion** → Implement TTLs
4. **User complaints** → Check content filters
5. **Bots talking to themselves** → Fix loop detection

## Definition of Done per Sprint

### Sprint 0 ✓
- [ ] Bot maintains connection 24+ hours
- [ ] Messages flow: Discord → Fargate → SQS → Lambda
- [ ] CDK deployment works
- [ ] Zero message loss

### Sprint 1 ✓
- [ ] 3 personality files created
- [ ] Each personality unique voice
- [ ] !roast command works
- [ ] <3 second responses

### Sprint 2 ✓
- [ ] Memory saves/loads correctly
- [ ] Context improves responses
- [ ] Inside jokes detected
- [ ] <100ms memory operations

### Sprint 3 ✓
- [ ] Rate limits enforced
- [ ] No toxic content passes
- [ ] Admin commands work
- [ ] Stable under spam

### Sprint 4 ✓
- [ ] 5 bots interact naturally
- [ ] No response loops
- [ ] Personality maintained
- [ ] Smooth updates

### Sprint 5 ✓
- [ ] Users influence bots
- [ ] Changes persist
- [ ] Natural integration
- [ ] Clear audit trail

### Sprint 6 ✓
- [ ] 80% test coverage
- [ ] Full monitoring
- [ ] Complete docs
- [ ] $30-50/month cost

## Emergency Contacts

- **Architecture Issues**: Pivot to EC2 (1 week delay)
- **Cost Overrun**: Implement caching layer
- **Content Problems**: Add human review queue
- **Performance Issues**: Add Redis cache
- **User Complaints**: Check personality configs

## The One Metric That Matters

**Week 1**: Bot uptime (target: 24 hours)
**Week 2**: Unique responses (target: 90% different)
**Week 3**: Memory recalls (target: 20/day)
**Week 4**: Safety blocks (target: <1% false positives)
**Week 5**: Multi-bot interactions (target: 100/day)
**Week 6**: User satisfaction (target: 4.5/5)
**Week 7-8**: Production stability (target: 99.9%)

## Ship It Checklist

Before going live:
- [ ] Fargate solution proven stable
- [ ] 3+ personalities tested extensively  
- [ ] Memory system handles 1000+ messages
- [ ] Safety filters catch bad content
- [ ] Costs confirmed under $50/month
- [ ] Documentation complete
- [ ] Monitoring dashboards live
- [ ] Incident response plan ready

**Remember**: Perfect is the enemy of good. Ship when Sprint 3 is done, iterate from there!