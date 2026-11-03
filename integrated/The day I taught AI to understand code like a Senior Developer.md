The day I taught AI to understand code like a Senior Developer

Apr 7 2025

Is it just me, or are the code generation LLMs we’re all using not that good?

For months, I’ve watched developers praise LLMs while silently cleaning up their messes, afraid to admit how much babysitting they actually need.

I realized that LLMs don’t actually understand codebases — they’re just sophisticated autocomplete tools (with good marketing.)

After two years of frustration watching my AI assistants constantly “forget” where files were located, create duplicates, and use completely incorrect patterns, I finally built what the big AI companies couldn’t — or wouldn’t.

I decided to find out: What if I could make AI actually understand how my codebase works?

# Illusion of Comprehension

Last December, I hit my breaking point. My supposedly “intelligent” AI kept generating components that didn’t follow our established patterns. When I pointed this out, it apologized — and then proceeded to make the exact same mistake ten minutes later.

This wasn’t a one-off. This was the norm.

The problem became clear: these AI tools don’t have any actual understanding of codebases as interconnected systems. They’re operating on small context windows and failing spectacularly at maintaining a mental model of the project.

What makes this particularly frustrating is how the marketing from major AI companies implies their tools “understand” your code. They don’t. They’re making educated guesses — and the difference becomes painfully obvious on any moderately complex project.

# Junior vs Senior Mindset

While thinking about this problem, I went back to first principles and tried to analyze how senior developers think about a codebase:

- Junior developers focus on “what” and “how” — they look at specific implementation details to solve immediate problems. They can write functioning code, but they often miss the bigger picture.
- Senior developers focus on “why” and “what if” — they maintain a mental model of the entire system, understand how components interact, and anticipate ripple effects of changes. They distinguish between code that’s incidental versus foundational.

I realized LLMs often operate like junior developers, not senior ones:

- They get lost in large codebases because they lack a high-level understanding.
- They write duplicate functionality rather than recognizing reuse opportunities.
- They operate on trial and error, rushing to write code without understanding the complete context.
- They follow patterns inconsistently, not grasping their underlying purpose.
 
My goal became clear: could I make AI think more like senior developers by helping improving its model of the codebase?

# Breakthrough

The solution came to me during a 2 AM coding session, while I was dealing with yet another incorrectly generated file: what if we treated the codebase as a hierarchical knowledge graph instead of flat files?

```
app
	models
		_init_.py
		user.py
		product.py
	utils
		_init_.py
		helpers.py
		cache.py
		parsers.py
	tests
		_init_.py
		test_user.py
		test_product.py
```

Human developers don’t memorize entire codebases. We build mental models of how components relate to each other. We understand that some code is boilerplate, while other sections are critical business logic. We naturally view code through different “lenses” depending on what we’re trying to accomplish.

I developed what I call “Ranked Recursive Summarization” (RRS), an algorithm that starts from the leaves of a project’s directory tree and recursively builds understanding upward using LLMs:

# pseudocode:
```
def ranked_recursive_summarization(folder):
    if is_file(folder):
        chunks = split_into_chunks(read_file(folder))
        ranked_chunks = rank_by_importance(chunks)
        return summarize(ranked_chunks)
    
    summaries = []
    for child in folder.children:
        summary = RRS(child)
        summaries.append(summary)
    
    return summarize(summaries)
```

This worked shockingly well, but I soon realized it wasn’t enough. Depending on what I was trying to work on, RRS missed certain details. If it had information about architecture and data models, it missed out on frontend components. If it was too focused on UI, it missed out on describing data flow.

I had to think deeper: what makes a certain part of the code important?

# Lensed Understanding

My second insight led to the truly transformative technique: “Prismatic Ranked Recursive Summarization” (PRRS).

Instead of having one global definition of “importance,” PRRS analyzes code through multiple conceptual lenses:

# pseudocode:
```
def prismatic_rrs(folder, lenses=['architecture', 'data_flow', 'security']):
    summaries = {}
    for lens in lenses:
        context = f"Analyze importance from {lens} perspective"
        summaries[lens] = RRS(folder, context=context)
    return summaries
```

The results were undeniable. AI suddenly understood:

- Where files should logically be placed
- Which patterns to follow
- How to extend existing abstractions instead of creating new ones
- When to reuse code vs. create new implementations
- Honestly, the approach isn’t particularly complex or compute-intensive. The big AI companies could have implemented something like this from the beginning. But they haven’t, because it doesn’t align with their incentives of getting results for the lowest token costs.

# Why This Matters

The implications go far beyond fixing basic errors. When AI truly understands your codebase:

- Technical debt becomes visible through the “architecture” lens
- Security vulnerabilities emerge naturally through the “security” lens
- Junior developers can navigate complex projects with senior-level insight
- Onboarding time for new team members decreases dramatically
- There’s a darker side as well. As AI gets better at understanding codebases, the value of certain types of programming knowledge decreases: the mid-level programmer who primarily translates requirements into code without architectural insight may find themselves increasingly squeezed.

After experimenting with these techniques for several weeks, I eventually packaged them into a tool called Giga AI. I built it initially to solve my own frustrations, but other developers kept asking to try it after seeing how it changed my workflow. Developers who use Giga report less time spent correcting AI-generated code, are able to ship faster, and feeling less frustrated.

# Implementation

Even without my specific tool, you can improve your AI assistant’s code understanding:

- Create manual summaries of your most important directories and files
- Ask an AI to further improve your manual documentation
- Create and ensure multiple documentation files, each from a different “lens”, based on your project
- Include relevant files into AI’s context as needed
- These approaches won’t be as seamless as a purpose-built solution, but they’ll dramatically improve your results compared to the default experience.

# Context is the Future

I believe we’re at the beginning of a fundamental shift in how AI understands complex systems like codebases. The next generation of tools won’t just create embeddings of your code — they’ll build rich mental models from multiple perspectives, just like experienced developers do.

The companies that embrace this approach will leapfrog those still focused on token prediction alone. And developers who learn to leverage these sophisticated tools will have sustainable advantages that mere “prompt engineering” can’t match.

The future belongs to those who see AI not as a replacement for human developers, but as a force multiplier for human ingenuity.

And that future starts now.

What frustrations have you experienced with AI? I’d love to hear your stories at hi@nmn.gl

P.S. My AI improves code generation in production & helps you ship faster. Loved by developers & teams all over the world. Check out Giga AI.