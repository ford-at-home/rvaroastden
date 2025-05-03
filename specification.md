# Technical Specification: AI Roast Den

## Overview

This document outlines the architecture, components, and expected behaviors for the AI Roast Den — a Discord-integrated system for deploying AI chat agents modeled after real people.

---

## System Components

### 1. Discord Listener

- **Language**: Python (discord.py)
- **Hosted On**: AWS Lambda via WebSocket relay or AWS AppRunner
- **Responsibilities**:
  - Listen to all messages
  - Detect @mentions and message content
  - Route input to appropriate agents via async Lambda invocation

### 2. AI Agent Engine

- **Backend**: Amazon Bedrock (Claude 3 Sonnet preferred)
- **Invocation**: Lambda per agent, triggered by dispatcher
- **Prompt Composition**:
  - System prompt from `/personalities/<agent>.yaml`
  - Recent message context (last 10 messages)
  - Long-term memory retrieved from DynamoDB
  - Current influence from their corresponding “higher self,” if active

### 3. Memory Store

- **Service**: DynamoDB
- **Tables**:
  - `short_term_memory`: Recent messages per channel
  - `long_term_memory`: Indexed facts, quotes, shared events per agent
- **Future Enhancement**: Vector embeddings with OpenSearch

### 4. Higher Self Integration

- Each human user has a special “higher self” identity in Discord.
- Messages from a higher self override or influence their bot’s system prompt.
- Bots prioritize input from their higher self but may respond independently.
- Bots will recognize and treat others’ higher selves with reverence, skepticism, or humor, based on internal persona logic.

### 5. Command System

- **Command Prefix**: `/`
- **Implemented Commands**:
  - `/remember`: Adds a memory to the agent
  - `/forget`: Removes a memory
  - `/mute <agent>`: Temporarily disable a bot
  - `/summon <agent>`: Force an agent to respond

### 6. Infrastructure

- **Infra-as-code**: AWS CDK (TypeScript or Python)
- **Secrets**: Stored in AWS Secrets Manager (Discord token, Bedrock creds)
- **CI/CD**: GitHub Actions with deployment hooks

---

## Interaction Logic

- Agents decide whether to speak based on:
  - Relevance of message content
  - Past context
  - Higher self input (if any)
  - Social model (e.g. if being roasted, roast back)
- Each response is generated within 5–8 seconds
- Responses include formatting, emojis, and styling in character

---

## Security & Limits

- Rate limits per user and per agent
- Auto-fallbacks if Bedrock fails (can use OpenAI)
- Moderation hooks if needed

---

## Scalability

- Fully serverless design (stateless Lambda agents)
- Horizontal scaling via async invocations
