# ✅ RVARoastDen Setup Checklist

This is a running checklist for building and launching the RVARoastDen Discord bot system.

---

## 🛠️ Core Infrastructure

- [x] Create Discord Application and Bot
- [x] Add Bot to Discord Server via OAuth2 URL
- [x] Turn OFF "OAuth2 Code Grant" setting
- [x] Create test Discord server with proper permissions
- [x] Store Discord bot token in AWS Secrets Manager
- [x] Create AWS CDK stack with:
  - [x] Lambda function
  - [x] Role with Secrets Manager + Bedrock access
  - [x] Discord token injected into Lambda via environment
- [x] Deploy CDK stack

---

## 🧠 AI Brain

- [x] Add `!ping` and `!hello` test commands
- [x] Add `!ask` command to call Claude via Bedrock
- [ ] Add roast response logic using Claude and prompt shaping
- [ ] Add per-agent persona file and personality injection
- [ ] Add Claude memory access via DynamoDB

---

## 💾 Memory System

- [ ] Add DynamoDB table via CDK
- [ ] Add long-term memory query/save logic to bot
- [ ] Inject memory into Claude prompts
- [ ] Allow `/remember` and `/forget` commands from Higher Self

---

## 🌐 Multi-Agent + Higher Self Mode

- [ ] Support multiple bots (Ford, Adam, April)
- [ ] Add identity recognition logic between bots
- [ ] Allow real users to act as Higher Selves in Discord
- [ ] Route Higher Self input into their respective bot memory/influence
- [ ] Respect Higher Self commands (e.g. “start a convo from scratch”)

---

## 🧪 Testing + Debugging

- [ ] Test bot response accuracy and tone
- [ ] Test roast logic across multi-agent interactions
- [ ] Confirm memory loading and updates
- [ ] Confirm Claude responses are in-character

---

## 🚀 Optional Enhancements

- [ ] Add Bedrock fallback to OpenAI for quality control
- [ ] Add Discord slash commands (e.g. `/summon`, `/mute`, `/vibecheck`)
- [ ] Build dashboard to visualize memory, command stats, etc.

---

## 🧬 You’ve Completed:

- Core bot creation and Discord integration ✅  
- Secrets Manager + CDK deployment ✅  
- Working lambda handler with Bedrock access ✅  

Next focus: **memory + roasting logic + multi-agent orchestration**
