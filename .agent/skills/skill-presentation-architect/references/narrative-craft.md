# Narrative Craft

Source: Sumeet Gayathri Moghe, "Nail your narrative" (15 September 2026), Never Send The Slides series, martinfowler.com.
URL: https://martinfowler.com/articles/never-send-slides/nail-your-narrative.html
This file is a methodological synthesis, not a reproduction. Series context: previous post "Do you even need a presentation?", next posts "Principles for effective slides" and "Build your slide template".

Shared by `skill-presentation-architect` and `skill-factory-creator` (see `skill-factory-creator/references/narrative-for-skills.md` for the skill-authoring mapping).

## Thesis

Narrative first, visuals next. A 16:9 slide forces the narrative to be sliced by visuals. Without a narrative, each slide triggers second-guessing, amplified by font, color, diagram, image, transition, and build decisions. Form precedes function. Canned slides are the shortcut presenters take to escape that load.

Pipeline: Big Idea -> Audience persona -> Storyline (structure + construction method) -> Voice-it-without-slides test -> Storyboard -> Slide design.

## Big Idea (after Nancy Duarte)

One speakable sentence = point of view + what is at stake.

- Point of view: contrarian take, new perspective, novel idea, practice to adopt.
- Stakes: why care, what is lost if they do not.
- Test: sentence rolls off the tongue, not a mouthful.

Worked example (Moghe): POV = brainstorming is a corporate superstition, brainwriting is better. Stakes = teams lose ideas to production blocking, conformity, dominant voices, social loafing. Big Idea = "Instead of brainstorming, a corporate superstition that kills your best ideas, adopt brainwriting and let independent judgment surface the widest range of ideas and the deepest thinking."

Uniqueness: useful provocation that sharpens the message, not mandatory. A known idea can be new to the audience. Replace "is this unique?" with "what point of view am I introducing to this audience?".

## Audience persona (5 steps)

1. Name them (example: Parul, the project lead).
2. Personify with a photo or stick figure; enables empathy while drafting.
3. Describe: role, prior experience and knowledge, goals, interests.
4. Say why they would care: the problem addressed, how their world improves.
5. List takeaways. Cap at three.

Effort scales with familiarity. Teammates: minutes, tweak per iteration. New client: invest in learning the audience.

Situation shapes the talk. Zoom with a boss and two colleagues drives conversation and decisions: flexible, tracks change. Main-stage keynote is authoritative, less conversational: a set play works.

## Storyline structures

| Structure | Stages | Fits |
| :--- | :--- | :--- |
| Sparkline | What is -> What could be, repeated beats | Change, strategy, vision |
| Explainer | Context -> Roadmap -> Steps -> Recap -> Celebrate (call to action) | Audience lacks a mental model |
| Pitch | Windup -> Hurdle -> Vision -> Options (mostly boring, one inspiring) -> Close -> Fine print (+ bonus) | Solution proposals, investment |
| Hook, Meat, Payoff | Provocative opener -> structured substance -> payoff tied to hook | Short punchy talks |
| Situation, Complication, Resolution | Situation -> BUT -> Complication/opportunity -> THEREFORE -> Resolution | Consulting-style decision briefs |
| Hero's Journey | Situation -> Challenge -> Crisis -> Rock bottom -> Comeback -> Emerging stronger | Project stories, incident retrospectives, experience reports |
| A la Carte (Neal Ford) | Menu of independent mini-storylines, audience picks | Unpredictable audiences, more content than time; high demand on speaker |
| Diagram-centric (additional, from series acknowledgments) | One core boxes-and-arrows diagram is the spine; nested slides and animations expand it | Architecture, causal flows, system boundaries |

Structure is the logic of the talk, not decoration. If none fit, invent one and justify it against the Big Idea.

## Four construction methods

1. **Collaborative whiteboarding.** Co-presenters; sticky notes (physical, Miro, Mural). Stickies move, edit, trash; color shows themes; proximity shows adjacency. Moghe publishes a Mural template with the story structures and big-idea/persona panels.
2. **Diagram-centric.** Sketch boxes and arrows first (notebook or slide); spend hours scribbling and noting; reproduce on a slide; build the deck with animations and nested slides around it.
3. **Narrative-based writing.** Solo presenters who think in text: bulleted structure, then fleshed prose. Google Docs templates exist per structure.
4. **Voice memo plus AI.** Pick structure, record thoughts per segment, transcribe (iOS Voice Memos, Android Recorder), pass transcripts to a chatbot to clean and structure. Custom skills push output toward a usable draft. Rule: do not outsource the thinking.

Success criterion for all four: the presenter can voice the narrative with no visual aid.

## Storyboard

Clarity on what to show. Simplest form: one note per slide, described as simply as possible. Sticky notes or index cards, or a document, or slides in slide-sorter / light-table view.

Slide-based storyboarding rule: resist designing. Limit to the spine: drop text and sample images, reorder panels. Polish later. Slide count does not matter when the presenter controls pace.

Start slow so you can go fast: working from a plan beats playing it by ear, and the upfront cost shrinks with repetition.

## Iteration and mastery

Narrative is not static. Storyboarding may adjust the narrative; design may challenge the storyboard, the narrative, and audience assumptions. The outline feeds the design; the design can challenge the outline.

Coaching observation (Moghe): novices benefit from the structured sequence; experts compress, skip, or bounce between steps without added cognitive load. Picasso: learn the rules like a pro so you can break them like an artist. Skill behavior: run the full sequence by default; compress only when USER shows fluency or says "just make the deck".

## Operationalization in this factory

| Moghe step | Artifact | Schema | Gate |
| :--- | :--- | :--- | :--- |
| Big Idea | `big_idea.sentence` | `schemas/narrative-brief.md` | `validate_storyboard.py --brief` |
| Persona + takeaways | `audience` | `schemas/narrative-brief.md` | max 3 takeaways |
| Storyline | `story.structure`, `story.beats` | `schemas/narrative-brief.md` | structure named + rationale |
| Voice-it test | Narrative prose in brief | SKILL.md section 5 | USER or model walkthrough without visuals |
| Storyboard | `storyboard[]` | `schemas/storyboard.md` | `validate_storyboard.py` |
| Design | `slide-spec` | `schemas/slide-spec.md` | render + inspect loop |
