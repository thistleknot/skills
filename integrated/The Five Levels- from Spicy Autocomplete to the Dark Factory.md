## The Five Levels: from Spicy Autocomplete to the Dark Factory

In my last post, I wrote about technical deflation. We're seeing the cost of code is dropping so fast that we need to change our tech debt payment plans. The smart teams are deferring payment on human hours today to pay them back with cheaper AI hours tomorrow.

But how do you actually cash in on those cheap hours?

If you are just using ChatGPT to write your regex, you aren't really getting the benefits of deflation. You're just typing faster.

I've now seen dozens of companies struggling to put AI to work writing code, and each one has moved through five clear tiers of automation. That felt familiar, and I realized that the federal government had been there first - but for cars.

In 2013, the NHTSA created the five levels of driving automation 1 . This was helpful, because while the highest level at the time was only level 2 2 , it let everyone have a common language for both where things were, and where things were going.

## SPICY AUTOCOMPLETE (Level 0)

The Al serves as a reference tool or enhanced search, like a smarter Stack Overflow. The developer manually writes all the code; using Al for specific snippets or answers.

<image_001>
An overhead view of a vintage car's interior, focusing on the driver's perspective. The driver, wearing a checkered shirt and a wristwatch, is seated in the driver's seat holding a wooden steering wheel. The dashboard features several circular gauges, including a speedometer and a tachometer, with a small digital display showing "182" in the center. There is a manual gear shift lever in the center console area. The dashboard and interior panels are in a beige and black color scheme. The car's interior design is characteristic of a classic model, with prominent chrome accents and a steering wheel with a wood finish.
</image_001>

Level Zero is your parents' Volvo, maybe with an automatic transmission. Whether it's vi or Visual Studio, not a character hits the disk without your approval. You might use AI as a search engine on steroids or occasionally hit tab to accept a suggestion, but the code is unmistakably yours. This is manual labor in a deflationary world.

## CODING INTERN (Level 1)

<image_002>
formatting
</image_002>

The Al writes unimportant or boilerplate code. The developer prompts for specific functions but immediately reviews and integrates the output.

At Level 1, you've got lanekeeping and cruise control. You're writing the important stuƯ, but you oƯload specific, discrete tasks to your AI intern. 'Write a unit test for this.' 'Add a docstring.' You could be using anything from copy-paste ChatGPT to Copilot. You're seeing speedups, but your job is unchanged. You're still moving at the rate you type.

## JUNIOR DEVELOPER (Level 2)

<image_003>
This image depicts the interior of a car from the driver's perspective, focusing on the steering wheel, dashboard, and the road ahead. A hand is visible gripping the steering wheel. The dashboard features two circular gauges (likely speedometer and tachometer) with numerical indicators and a red needle on the tachometer. To the right of the steering wheel, there is a digital display showing "F5" and "08:45" along with some text. The road appears to be a multi-lane highway with several vehicles visible in the distance, and the background includes mountains and some vegetation. There are guardrails on the left side of the road, and the image has a slightly hazy sky. The interior of the car appears to be a typical modern sedan with a dark dashboard and a light gray steering wheel.
</image_003>

An interactive 'pair programmer' partnership. The developer and Al trade off control; with the human reviewing code as its generated in real-time.

At Level 2, you've got Autopilot on the highway. As a coder, you feel free. You've got a junior buddy to hand oƯ all your boring stuƯ to. This is where 90% of 'AI-native' developers are living right now. You are pairing with the AI like a colleague. You get into a flow state; you're more productive than you've ever been. You're not using chat, you're getting real mileage out of an AI-native coding tool. But here is the danger: level 2, and every level after it, feels like you are done. But you are not done.

## DEVELOPER (Level 3)

<image_004>
formatting
</image_004>

The Al generates the majority of the codebase. The developer reviews everything the Al does; acting as the bottleneck for verification before progressing.

Level 3 is a Waymo with a safety driver. You're not a senior developer anymore; that's your AI's job. You are… a manager. You are the human in the loop. Your coding agent is always running multiple tabs. You spend your days reviewing code. So much code. Your life is diƯs. For many people, this feels like things got worse.

And almost everyone tops out here.

## ENGINEERING TEAM (Level 4)

<image_005>
formatting
</image_005>

The Al runs unattended for long periods; handling complex tasks: The human trusts the system's selfchecks; only checking the final results much later.

Level 4 is a robotaxi, and while it's driving, you can do something else. You're not a developer. You're not a development manager either. You've now become that which you loathed: you're a PM 3 . You write a spec. You argue with it about the spec. You craft skills (for Claude Code, because most folks at level 4 seem to find their way to Claude Code). You plan schedules. You review plans. Then you leave for 12 hours, and check to see if the tests pass.

I'm here.

## DARK SOFTWARE FACTORY (Level 5)

<image_006>
formatting
</image_006>

The engineer manages the goals and the system; not the code. provide English descriptions. The Al defines implementation; writes code; tests; fixes bugs; and They plain ships.

At level 5, it's not really a car any more. You're not really running anybody else's software any more. And your software process isn't really a software process any more. It's a black box that turns specs into software.

Why Dark? Maybe you've heard of the Fanuc Dark Factory, the robot factory staƯed by robots. It's dark, because it's a place where humans are neither needed nor welcome.

I know a handful of people who are doing this. They're small teams, less than five people. And what they're doing is nearly unbelievable - and it will likely be our future.

<image_007>
This image is a section from a document titled 'THE EVOLUTION OF AI-ASSISTED SOFTWARE DEVELOPMENT', presented as a grid of six rectangular panels, each depicting a different stage of AI in software development. The panels are arranged in two rows of three. The top row is labeled 'SPIICY AUTOCOMPLETE (Level 0)', 'CODING INTERN (Level 1)', and 'JUNIOR DEVELOPER (Level 2)'. The bottom row is labeled 'DEVELOPER (Level 3)', 'SENIOR DEVELOPER (Level 4)', and 'SOFTWARE FACTORY (Level 5)'. Each panel contains a photograph of a car interior showing an occupant (driver or passenger) interacting with an AI system, with overlaid text describing the AI's role at each level. The panels are visually consistent with car interior scenes, using a similar style of dashboard and steering wheel. The text in each panel is descriptive and specific, with detailed explanations of the AI's function and interaction with the developer. Key visual elements include the car interior shots and the clear labeling of each development stage. The document is structured in a chronological fashion, moving from basic AI assistance (Level 0) to more advanced roles involving human and AI collaboration. All the text elements are factual and precise, describing the AI's roles at each level. There are no charts, tables, or diagrams beyond the descriptive text; the key visual elements are the car interior shots and their associated labels. All elements in the image are informative and part of the document's content.
</image_007>

Thanks to Jesse Vincent, Justin Massa, Ramon Marc, Tenzin Wangdhen, and Noah Radford (who wrote this incredible piece) for reading drafts of this.

1. Actually they made four, which was really five because it was zero-based. Then they realized they had to add a fifth. Which was actually the sixth. ↩
2. The 2014 Mercedez-Benz S-Class Distronic Plus with Steering Assist. Who says AI companies have a monopoly on catchy names? ↩
3. Program manager? Project manager? Product manager? Yes. ↩