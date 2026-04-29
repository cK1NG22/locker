# Locker — User Test Results

---

## Test #1
**Tester name:** Adam (brother)
**Why is this person a good tester?** Computer science student, uses VS Code and Cursor daily, fits our ICP of a developer on a small team who'd benefit from shared AI skills.
**Date:** March 8, 2026

**Task given:** "Imagine your team lead sent you this invite link and told you to set up Locker so you can use the team's AI skills in Claude Code. Go ahead and try."

### Observations
- **Could they complete the core task?** Partially
- **Time to complete:** 11 minutes (target was under 3)
- **Where did they get stuck?** After clicking the invite link and signing in with Google, he landed on the dashboard and could see the team's skills. That part was smooth. The problem was the setup token — he clicked "Copy Setup Token," pasted it into the terminal, but the token had already been rotated by the time he ran the command. Got a 401 error. He tried generating a new one, same issue. Had to ask me what was happening.
- **Where did they click wrong things or hesitate?** Clicked "Settings" first instead of "Setup" — expected setup instructions to be in settings. Also hesitated on the terminal command, wasn't sure if he needed to restart Claude Code after running it.
- **What did they say out loud?** "Wait, it says unauthorized. I literally just copied this." ... "Do I need to restart something?" ... "OK the skills part is actually really cool once it works."
- **Facial expressions / body language:** Visibly frustrated during the token failure. Leaned back, sighed. Perked up once he got a skill to actually run — said "oh that's sick" when the skill content appeared in Claude Code.

### Follow-up Responses
- **What was confusing?** "The setup token thing. I don't know why it expired. I just copied it 30 seconds ago." Also didn't know what MCP was — the setup instructions reference it but don't explain it.
- **What would they change?** "Just give me a password or something simple. I don't need rotating tokens for a team tool."
- **Would they use this again?** "Yeah, once it's set up it's great. The setup just needs to not fight you."

### Severity of Issues Found
- **Critical:** Setup token expiring before use — user cannot complete onboarding without help
- **Major:** No clear indication of what to do after signing in (setup vs. settings confusion)
- **Minor:** No explanation of what MCP is for non-experts

---

## Test #2
**Tester name:** Alex (brother)
**Why is this person a good tester?** Works in IT support, comfortable with terminal but not a daily coder. Represents the "technical but not developer" segment of our target users — team members who use AI tools but aren't power users.
**Date:** March 8, 2026

**Task given:** "You just joined a new team that uses Locker to share AI coding skills. Here's the invite link — get yourself set up and try using one of the team's skills."

### Observations
- **Could they complete the core task?** Yes, but with significant difficulty
- **Time to complete:** 8 minutes
- **Where did they get stuck?** Same token issue as Adam but he got lucky — his token worked on the first try. The bigger problem for him was the terminal setup. He wasn't sure where to paste the setup command. He opened Terminal instead of the Claude Code terminal. Once I pointed him to Claude Code (without explaining further), he figured it out. After setup, calling a skill with `/locker list_skills` worked first try.
- **Where did they click wrong things or hesitate?** Tried to click on a skill name in the dashboard expecting it to "run" the skill. Didn't realize skills are consumed in the terminal, not the web UI. Took a minute to understand the dashboard is for managing, terminal is for using.
- **What did they say out loud?** "Where do I paste this?" ... "Oh wait, I need to be in Claude Code, not regular terminal?" ... "OK so the website is just for seeing what's available. Got it."
- **Facial expressions / body language:** Looked uncertain during setup, kept glancing at me for reassurance. Once he called a skill successfully, nodded and said "that makes sense."

### Follow-up Responses
- **What was confusing?** "I didn't know the website and the terminal were two separate things. I thought I'd use the skill from the website." Also mentioned the setup token was "intimidating" — long random string felt like something he could break.
- **What would they change?** "A simpler login. Like a team password. Or just make the invite link do everything automatically."
- **Would they use this again?** "If someone set it up for me, definitely. The skill part is useful. Setup is the only barrier."

### Severity of Issues Found
- **Critical:** Setup token UX causes confusion and auth failures
- **Major:** Mental model mismatch — users expect to use skills from the dashboard, not the terminal
- **Minor:** Setup command doesn't clarify which terminal to use (Claude Code vs. system terminal)

---

## Test #3
**Tester name:** Clark (cousin)
**Why is this person a good tester?** Freelance web developer, uses Claude Code regularly for client projects. Closest match to our core ICP — an active Claude Code user who would directly benefit from shared team skills.
**Date:** March 9, 2026

**Task given:** "Your team just started using Locker to share AI skills. Here's the invite link. Set it up and try calling a skill."

### Observations
- **Could they complete the core task?** Yes
- **Time to complete:** 4 minutes
- **Where did they get stuck?** Barely. He already knew what MCP was, so the setup concept made sense. He did hit the token rotation issue — copied the token, switched to Claude Code, pasted the setup command, and it worked (he was fast enough). His one stumble was that after running setup, he typed `/locker` expecting a help menu, but got a "skill not found" error because he didn't include a skill name.
- **Where did they click wrong things or hesitate?** None on the dashboard side — navigated directly to Setup, copied the token, ran the command. On the Claude Code side, he hesitated after `/locker` failed, then tried `/locker list_skills` which worked.
- **What did they say out loud?** "Oh nice, it's MCP-based. That's clean." ... "Hmm, just `/locker` by itself should probably show available skills." ... "This is actually really useful. I'd set this up for my contractors."
- **Facial expressions / body language:** Engaged the whole time. Leaned in when reading skill descriptions. Smiled when a skill successfully loaded into his conversation.

### Follow-up Responses
- **What was confusing?** "Nothing major. The token thing is a little enterprise-y for a small team. A team password would be easier. But it works." Also suggested `/locker` with no arguments should default to listing skills instead of erroring.
- **What would they change?** "Team password instead of rotating tokens. And make `/locker` by itself show the skill list."
- **Would they use this again?** "100%. I'd actually pay for this. I have 3 contractors and I keep sending them markdown files with prompts. This would replace that entirely."

### Severity of Issues Found
- **Critical:** None
- **Major:** `/locker` with no arguments errors instead of showing help or skill list
- **Minor:** Token-based auth feels heavyweight for small teams

---

## Synthesis

### Overall Findings
All three testers successfully used Locker's core feature — calling a team skill from Claude Code via MCP — and found it genuinely useful once set up. The unanimous pain point was onboarding. The setup token workflow created friction for every tester: tokens that expired before use (critical for 1 of 3 testers), confusion about where to run the setup command, and a general sense that the auth mechanism was more complex than the use case warranted. Once past setup, the experience was smooth — skill discovery and execution worked as expected, and all three testers said they'd use it again.

### Issues by Severity

**Critical (1 issue)**
- Setup token rotation causes auth failures during onboarding. Tokens can expire between copying from the dashboard and pasting into the terminal. 1 of 3 testers was completely blocked; 1 was nearly blocked. This is the #1 barrier to adoption.

**Major (2 issues)**
- Mental model gap between dashboard and terminal. Non-developer testers expected to "use" skills from the web UI, not realizing the dashboard is for management and the terminal is for consumption.
- `/locker` with no arguments returns an error instead of help text or a skill list. New users don't know the exact command syntax.

**Minor (3 issues)**
- No explanation of MCP for non-technical users in setup instructions.
- Setup command doesn't specify "run this in Claude Code" vs. a regular terminal.
- Token-based auth feels unnecessarily complex for small teams (even when it works).

### Patterns Across Testers
- **3/3** found the core skill-calling feature valuable and said they'd use it again
- **3/3** struggled with or commented negatively on the setup token workflow
- **2/3** were confused about where to run the setup command (which terminal)
- **2/3** independently suggested a team password as a simpler alternative to tokens

### Key Quotes
> "Just give me a password or something simple. I don't need rotating tokens for a team tool." — Adam

> "If someone set it up for me, definitely. The skill part is useful. Setup is the only barrier." — Alex

> "This is actually really useful. I'd set this up for my contractors." — Clark

> "Oh that's sick" — Adam, after successfully calling his first skill

### Top 3 Prioritized Changes

1. **Replace setup tokens with team passwords** — The rotating token was the only critical issue found. A static team password (entered once during setup) eliminates expiration failures and reduces cognitive load. All 3 testers independently suggested this. *Status: Implemented after testing.*

2. **Add onboarding guidance after sign-in** — First-time users need a clear "here's what to do next" flow: step 1 copy this password, step 2 run this command *in Claude Code*, step 3 try `/locker list_skills`. Addresses the setup-vs-settings confusion and the "which terminal" problem.

3. **Default `/locker` to list skills** — When a user types `/locker` with no arguments, show available skills instead of an error. Reduces the learning curve and matches the mental model of "I just want to see what's available."
