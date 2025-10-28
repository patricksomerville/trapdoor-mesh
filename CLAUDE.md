# CLAUDE.md - Trapdoor Project Philosophy

## What This Is

**Trapdoor is personal infrastructure for operating with advantages as a small, agile individual.**

This is not a product to scale. This is not for everyone. This is a tool built to solve real problems for Patrick and his team - to enable one person to operate with capabilities typically reserved for larger organizations.

## Core Philosophy

**Build for yourself. Ship to yourself first. Find pain, fix pain.**

The best tools solve your own problems. Trapdoor exists because:
- You need to give multiple AIs safe, scoped access to your filesystem and processes
- You need to audit what happens when models interact with your system
- You need to be able to revoke or limit access without rebuilding integrations
- You need this to work reliably, right now, for real work

## Strategic Position

**Not to scale — to be ahead of the curve.**

You're building leverage:
- A solo operator with the right automation can outmaneuver entire teams
- Small size is an advantage: you can move fast, experiment, break things
- The goal is asymmetric capability, not market share

## What Matters

**✅ Do This:**
- Use it yourself for real projects
- Fix things that annoy you
- Add features when you hit actual pain points
- Make it reliable for YOUR workflow
- Build advantages that compound

**❌ Don't Do This:**
- Package for distribution
- Write protocol specs
- Add features because they sound cool
- Build for hypothetical users
- Optimize for scale

## Current State

Trapdoor is a production-ready system for:
- Multi-token authentication with scoped permissions
- Safe filesystem and process access from any LLM
- Rate limiting and approval workflows
- Audit logging of all operations
- Model-agnostic API (OpenAI-compatible + custom endpoints)

The security system we just built gives you something most companies don't have: **fine-grained control over what AI agents can do on your machine.**

## What "Operating with Advantages" Means

1. **Speed** - You can deploy a new capability in hours, not months
2. **Control** - Every AI interaction is logged, scoped, and revokable
3. **Flexibility** - Switch models, providers, tools without rebuilding
4. **Privacy** - Everything runs locally, nothing leaves your machine unless you allow it
5. **Leverage** - One person with good automation beats a committee without it

## Next Steps (When You Hit Them)

These aren't a roadmap. They're things that will matter when they matter:

- **Dashboard** - When you can't tell what's happening from logs alone
- **Token rotation** - When manually editing JSON feels too slow
- **Memory scopes** - When you want some agents to read but not write memory
- **Approval notifications** - When you need to know something's waiting
- **Multi-machine** - When you need this on more than one computer

Don't build any of these until you need them.

## For Future Collaborators

If you're reading this because you're helping with Trapdoor:

This is Patrick's tool. The goal is to make Patrick more capable.

That means:
- Bias toward simplicity over features
- Ship working things, not perfect things
- Ask "does this solve a real problem Patrick has?" before building
- If it doesn't make the user more capable, it doesn't belong

## The Boundary Layer

Most people are building bigger models.

Trapdoor is the boundary layer between human and model - where trust, control, and capability live.

That boundary is what matters. Get it right for yourself first. Everything else is optional.

---

**Last Updated:** 2025-10-28
**Status:** Production - Enhanced security system deployed and working
**Current Focus:** Use it. Find pain. Fix pain.
