---
name: git-workflow
description: >
  Git branching and push strategy for thistleknot/skills repository. Use this
  skill to understand when to create branches, when to push to dev vs main,
  and approval gates before merging to main. Ensures all work goes through
  proper review before reaching the canonical main branch.
---

# Git Workflow — Branch Strategy and Push Gates

## Branch Hierarchy

```
main          (canonical source of truth, merge-to-deploy)
  ↑ (merged by user via confirm)
dev           (integration branch, user-tested before main)
  ↑ (pushed by agent after user confirms working)
test/*        (feature/fix branches, agent working space)
```

## Workflow Rules

### 1. Work on Test Branches

**When to create a test branch:**
- Starting any new feature, fix, skill, or integration task
- Branch naming: `test/<feature-name>` or `test/<task-description>`
- Example: `test/megaprompter-extraction`, `test/sync-script-fix`

**Commands:**
```bash
git checkout -b test/<feature-name>
# Make changes, commit with signed co-author trailer
git commit -m "Descriptive message
Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### 2. Push to Dev — After User Confirms Working

**When to push to dev:**
- User has verified that the feature/fix works correctly
- All local tests pass (if applicable)
- Code review completed (if team protocol requires)
- User explicitly says "confirmed working" or similar approval

**Commands:**
```bash
git push origin test/<feature-name>    # Push test branch first
git checkout dev
git merge test/<feature-name>
git push origin dev                     # Push to dev only after merge
```

### 3. Push to Main — After User Confirms Dev Works

**When to push to main:**
- User has tested the changes on the dev branch and confirmed they work
- Dev integration testing is complete
- User explicitly approves: "push to main" or "ready for main"

**Commands:**
```bash
git checkout main
git pull origin main                    # Ensure local main is current
git merge dev
git push origin main                    # Push to main only after user confirmation
```

## Pre-Push Checklist

Before pushing to dev or main, verify:

- [ ] Code changes are complete and tested locally
- [ ] Git log shows clean commit history (no merge commits unless intentional)
- [ ] All commits have the signed co-author trailer
- [ ] No .git/, .gitignore, junk files synced (WinSCP filemask correct)
- [ ] README.md updated if skills or architecture changed
- [ ] Remote sync not yet performed (will happen after user confirms)

## LLM Work Verification Against Last Known Working Commit

**Critical: Before completing any task, always verify your changes against the last known working commit.**

### Verification Protocol

1. **Identify the baseline commit:**
   ```bash
   git log --oneline -10
   git show <last-known-working-commit>
   ```

2. **Compare your changes:**
   ```bash
   git diff <last-known-working-commit>..HEAD
   git status
   ```

3. **Checklist for each change:**
   - Does the diff show ONLY intentional changes for this task?
   - Are there unexpected deletions or overwrites?
   - Did you modify files you shouldn't have touched?
   - Are there new junk files (*.pyc, __pycache__, .DS_Store, etc.)?

4. **Run validation if applicable:**
   ```bash
   python -m py_compile <all-python-files>  # Syntax check
   git diff --check                          # Trailing whitespace check
   ```

5. **If anything is wrong, revert before pushing:**
   ```bash
   git reset --hard <last-known-working-commit>
   # Start over or ask user
   ```

### When to Check

- **After every major change**: Edit skill files, update README, modify scripts
- **Before each push to dev or main**: Non-negotiable
- **After merging branches**: Ensure merge didn't lose changes
- **When resuming work across sessions**: Compare current state to saved checkpoint

### What "Working" Means

A commit is "last known working" when:
- User explicitly confirmed: "working", "verified", "confirmed"
- Tests passed (if applicable)
- Remote sync completed successfully
- No reported issues from user

### Red Flags (Always Revert)

- Diff shows unrelated file changes
- New files appeared that you didn't create
- Modified files you explicitly decided not to touch
- Commit message doesn't match the actual changes
- Multiple unrelated features mixed in one commit

## Paired/Dimensional Feature Testing (Feature Expansion Validation)

**Principle: Test two things at once to prove feature extensibility, not just basic functionality.**

When verifying that a feature works, don't test it in isolation. Test two instances with different dimensions/conditions to prove that the feature is truly extensible and allows new variations.

### Pattern: Feature + Variant Testing

**The Problem:**
- Testing a single feature case doesn't prove the feature is real
- Example: "Can we add a unit?" tested by adding one unit doesn't prove we can add *different types* of units

**The Solution:**
- Test the base feature: Add Unit 1 with default/existing tech
- Test a variant: Add Unit 2 with NEW tech that requires NEW conditions
- This proves: (1) feature works, (2) feature is extensible, (3) new conditions can be enabled

### Example Workflow

**Scenario: Adding units to a system**

❌ **Incomplete test (don't do this):**
```
Feature: "Can add a unit"
Test: Add one unit with default tech
Result: ✅ One unit added
Proof: "Feature works"
Problem: Doesn't prove system can handle DIFFERENT units or conditions
```

✅ **Complete test (do this instead):**
```
Feature: "Can add units with different tech prerequisites"
Test 1: Add Unit A with Tech X (already available)
        Result: ✅ Unit A renders correctly
        
Test 2: Add Unit B with Tech Y (new tech, NOT available by default)
        Result: ✅ Unit B only appears when Tech Y is unlocked
        
Proof:
  - Base feature works (Unit A with default tech)
  - Feature is extensible (Unit B with new conditions)
  - Conditional enabling works (Unit B hidden until Tech Y acquired)
  - Artifacts: before/after screenshots, both unit types visible
```

### Validation Checklist for Paired Testing

- [ ] Base feature tested with existing/default tech (proves basic functionality)
- [ ] Variant feature tested with NEW tech/conditions (proves extensibility)
- [ ] Both are visible/testable in same session (proves coexistence)
- [ ] Variant only appears when NEW conditions met (proves conditional logic)
- [ ] Artifacts show both (screenshots, test logs, or proof of state)
- [ ] Diff shows new conditionals/branching logic added (not just copying base)

### Why This Matters

**Single test:** Feature might work by accident with hardcoded paths
**Paired test:** Proves feature can handle variations and new dimensions

Example: A "unit addition" feature that works for Unit A might have hardcoded assumptions about name, tech, stats, etc. Adding Unit B with different assumptions proves those aren't hardcoded.

### Red Flags (Incomplete Testing)

- ❌ Only one unit added, other functionality unchanged
- ❌ New unit is just a copy with different name (no new logic)
- ❌ No new tech/conditions added (nothing extensible to test)
- ❌ Only happy-path tested; variant doesn't appear in validation
- ❌ No artifacts showing both units/variants side-by-side

## Co-Author Trailer

All commits must include the Copilot co-author trailer:

```
Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

**Example commit:**
```
commit abc123def456
Author: User <user@example.com>
Date:   Sat May 03 15:04:15 2026 -0700

    Add react-fastapi-sqlite skill to README

    - Adds skill to execution/ section
    - Documents integration points with code and validation
    - Includes Key Relationship entry

    Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

## Remote Sync Strategy

**When to sync to remote (192.168.3.17):**
- After changes are pushed to main
- User runs `.\sync_skills.ps1` interactively
- WinSCP mirrors files with filemask exclusions
- Remote `/root/.copilot/skills` stays in sync with main

**Never sync:**
- Directly from test branches
- Before user approval
- Unverified changes

## Merge Conflict Resolution

If conflicts arise during merge:

```bash
# Examine conflicts
git status

# Resolve manually or use ours/theirs strategy
git checkout --ours <file>              # Keep local version
git checkout --theirs <file>            # Take remote version

# After resolution
git add <resolved-files>
git commit -m "Resolve merge conflict..."
```

## Undoing Mistakes

**If you push to main prematurely:**
```bash
# Revert the commit
git revert <commit-hash>
git push origin main

# OR reset and force-push (only if not yet on remote)
git reset --hard HEAD~1
git push -f origin main  # Use with caution; requires force flag
```

**If you need to rollback changes:**
```bash
# On dev or main
git reset --hard <commit-hash>
git push -f origin <branch>
```

## Integration with Copilot CLI

When working in the Copilot CLI:

1. **Agents must NOT push to main directly**
2. **Agents must ask user before pushing to dev**
3. **Agents must confirm user has tested before pushing to main**
4. **All work lives on test/* branches until explicit approval**

### Typical Agent Flow

```
1. git checkout -b test/task-name
2. Make changes, commit with trailer
3. Ask user: "Ready to push to dev?"
4. User confirms → git push to dev
5. User tests on dev → "Confirmed working"
6. Ask user: "Ready for main?"
7. User approves → git push to main
```

## Integration with Headless Browser Verification

**Verification Workflow: Code + Visual (for web frontend changes)**

The LLM work verification protocol pairs with `headless-browser-verification` specifically for web frontend changes:

### Code Layer (git-workflow) — All Changes
1. Compare changes against last known working commit: `git diff <baseline>..HEAD`
2. Verify no unintended modifications: Check for junk files, unexpected deletions
3. Run validation: Python syntax checks, trailing whitespace, linting
4. Red flag detection: Catch mixed concerns, unrelated edits

### Visual Layer (headless-browser-verification) — Web Frontend Only
**Required when:**
- Changes affect HTML/CSS rendering
- JavaScript UI interactions modified
- Responsive design affected
- Layout or styling changed
- Frontend components added/modified

**Not required when:**
- Backend-only changes (Python, Go, database, API)
- Configuration or infrastructure changes
- Documentation updates
- Test file changes
- Build/tooling changes

### Combined Verification Before Push (Frontend Changes)

```
Frontend Code Change → git diff check → CSS/HTML/JS validation ✓
                     ↓
                Commit to test/*
                     ↓
User asks to verify → Capture PNG screenshot → Compare visual
                     ↓
Visual matches intent? → All checks pass → Push to dev
```

**Example Workflow (Frontend):**
```bash
# 1. Make HTML/CSS/JS changes
git diff <baseline>..HEAD  # Verify code changes only

# 2. Start dev server and capture visuals
npm run dev               # Start http://localhost:3000
headless-browser-verify http://localhost:3000 \
  --output=screenshots/before-fix.png

# 3. Show user both code diff and visual proof
"Here's the git diff (only touching buttons.css and header.html)
 Here's the visual proof (screenshot shows responsive buttons at all breakpoints)"

# 4. User confirms both look good → push to dev
```

**Example: Backend Changes (No Visual Verification)**
```bash
# 1. Make backend changes (Python, FastAPI routes)
git diff <baseline>..HEAD  # Verify code changes only

# 2. Run tests/validation (no visual verification needed)
python -m pytest tests/api_test.py

# 3. Push to dev when user confirms
"Backend API routes updated and tests passing. Ready for dev?"
```

## Key Relationships

- **headless-browser-verification**: Visual verification paired with code verification; **required for frontend changes** before push gates
- **agentic-harness**: Owns the retry/gate logic for merges
- **continuity-log**: Tracks branch state across sessions
- **documentation**: Updated when README.md changes
- **code**: Follows branch strategy for all code changes
- **skill-wiki**: New skills go through test→dev→main progression

## References

- **Co-author trailer**: GitHub Copilot CLI standardized format
- **WinSCP filemask**: Excludes .git/, .gitignore, and junk files during sync
- **Repository**: thistleknot/skills on GitHub
<!-- consolidation:see-also:start -->
## See Also
[[substrate-selection]]  [[code]]  [[doc-synthesizer]]
<!-- consolidation:see-also:end -->
