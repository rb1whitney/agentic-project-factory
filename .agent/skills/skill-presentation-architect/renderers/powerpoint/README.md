# PowerPoint Renderer

## Role

Convert the approved canonical narrative + storyboard + slide specs into an editable `.pptx`.

The renderer is platform-specific. It should not reinterpret the narrative unless a rendering constraint exposes a genuine communication problem.

## Required output

- editable PowerPoint;
- 16:9 widescreen;
- speaker notes;
- native text;
- native shapes where practical;
- editable charts where practical;
- diagrams as editable shapes or SVG when native construction would materially reduce fidelity.

## Rendering contract

Input:
- `narrative-brief`
- approved `storyboard`
- `slide-spec`
- design tokens

Output:
- `.pptx`
- optional rendered slide images for QA
- QA report

## Layout rules

- 60px safe margin equivalent;
- no object outside safe bounds unless intentionally used as bleed;
- preserve hierarchy;
- never shrink typography below the approved minimum merely to fit content;
- reduce content before reducing readability.

## Visual rules

Prefer:
- native PowerPoint shapes;
- SVG for complex diagrams;
- editable charts;
- text boxes with semantic names where the platform supports them.

Avoid:
- screenshots of entire slides;
- flattened text;
- rasterized diagrams when editable alternatives are practical;
- decorative templates that compete with the narrative.

## QA loop

1. Generate.
2. Render.
3. Inspect each slide.
4. Inspect contact sheet / slide sorter.
5. Identify defects.
6. Revise.
7. Re-render.
8. Deliver only after final inspection.

## Renderer independence

The portable core owns:
- narrative;
- evidence;
- storyboard;
- visual thesis;
- slide semantics.

The renderer owns:
- PowerPoint geometry;
- object construction;
- theme application;
- notes;
- rendering;
- artifact inspection.
