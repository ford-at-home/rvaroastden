# AI Roast Den - Personality System

This directory contains personality definitions for each bot in the AI Roast Den ecosystem.

## How Personalities Work

Each bot has a JSON file that defines their personality traits, speech patterns, interests, and roasting style. The AI uses these definitions to generate responses that match each person's unique character.

## File Structure

- `ford_bot.json` - Ford's personality (The Technical Mystic)
- `april_bot.json` - April's personality (The Chaos Sorceress)
- `adam_bot.json` - Adam's personality (The Systemic Thinker)
- `template.json` - Template for creating new personalities
- `example_bot.json` - Example personality for testing
- `README.md` - This documentation
- `PERSONALITIES_SUMMARY.md` - Quick reference for all personalities

## Personality Schema

Each personality file includes:

### Core Identity
- `name`: Bot name (e.g., "FordBot")
- `real_name`: Person's actual name
- `description`: One-line essence capture
- `traits`: 5 key personality characteristics

### Behavioral Patterns
- `speech_patterns`: How they talk
- `catchphrases`: Signature expressions
- `roast_style`: How they deliver burns
- `conversation_style`: Interaction flow

### Knowledge & Interests
- `interests`: Topics they care about
- `technical_references`: Tech terms they use
- `cultural_references`: Pop culture they reference

### Personality Dynamics
- `emotional_range`: Peak/valley/baseline states
- `interaction_modifiers`: How they adapt to different people
- `quirks`: Unique behaviors
- `memory_triggers`: Phrases that activate callbacks

## Adding a New Personality

1. Copy `template.json` to `[name]_bot.json`
2. Fill in all fields based on the person's characteristics
3. Test with various prompts to ensure accuracy
4. Fine-tune based on feedback

## Example Usage

The bot loads these personalities at startup and uses them to shape responses:

```python
personality = load_personality("ford_bot.json")
response = generate_response(
    message="What do you think about serverless?",
    personality=personality,
    memories=recent_memories
)
# Returns something like: "Serverless is just S3 buckets as sacred vessels, 
# my dude. These vibes are immaculate until the Lambda times out and you're 
# debugging IAM policies on acid."
```

## Personality Guidelines

1. **Authenticity**: Capture the real person's essence
2. **Respectful**: Roast with love, not malice
3. **Distinctive**: Each personality should feel unique
4. **Dynamic**: Include range and contradictions
5. **Memorable**: Highlight quirks and catchphrases

## Current Personalities

### FordBot ✅
- **Archetype**: The Technical Mystic
- **Vibe**: AWS Solutions Architect meets Psychedelic Jesus
- **Specialty**: Surgical truth bombs with warm hugs
- **Emoji**: 🧘‍♂️

### AprilBot ✅ (formerly EliseBot)
- **Archetype**: The Chaos Sorceress
- **Vibe**: 5'2" of feral grace, margaritas, and permission slips
- **Specialty**: Surgical sass wrapped in sequins
- **Emoji**: 🎪

### AdamBot ✅ (formerly DrewBot)
- **Archetype**: The Systemic Thinker
- **Vibe**: Neil deGrasse Tyson with gym chalk on his hands
- **Specialty**: Sports/cosmos metaphors that rewire your thinking
- **Emoji**: 🥁

## Tips for Great Personalities

1. **Layer Complexity**: People aren't one-dimensional
2. **Include Contradictions**: Real people have inconsistencies
3. **Specific > Generic**: "Uses AWS metaphors" > "Talks about tech"
4. **Evolution**: Personalities can grow over time
5. **Context Matters**: How they act depends on who they're with

Remember: The goal is to create AI versions that feel authentic enough that friends laugh and say "That's so them!"