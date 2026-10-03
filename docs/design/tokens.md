# Design tokens v0.1

- **Status:** Draft, 2026-10-03 (principal-designer). Design review at the ST-010 PR [DPA/DESIGN-15].
- **Source of truth:** [`tokens.json`](tokens.json). The web app (ST-010, senior-frontend-engineer) maps them to CSS custom properties: `--color-<name>` for the active theme, plus `--space-*`, `--size-*`, `--font-*`. Do not hard-code colours in components.
- **Requirements:** NFR-029 (contrast), NFR-028 (target size), NFR-031 (focus not obscured), NFR-034 (reflow, colour). Sprint 0 ST-010 acceptance note: "Design tokens from the principal-designer meet 4.5:1 text and 3:1 non-text contrast".
- **Sources:** text contrast 4.5:1, or 3:1 for large text, SC 1.4.3 AA [DPA/DESIGN-03]; UI components and graphical objects 3:1, SC 1.4.11 AA [DPA/DESIGN-04]; targets 24×24 CSS px, SC 2.5.8 AA [DPA/DESIGN-02]; 48 dp touch targets [DPA/DESIGN-10]; focus not obscured, SC 2.4.11 AA [DPA/DESIGN-07].
- **Related ADR:** 0016 (design tokens and the contrast proof).

## 1. How the contrast proof works

`docs/design/tools/contrast_check.py` reads `tokens.json` → `contrastPairs`. It computes the WCAG 2.x relative luminance and the ratio `(L1 + 0.05) / (L2 + 0.05)` for every pair, then fails (exit 1) on any pair below its minimum. Semi-transparent colours, such as the video scrim, are composited over a declared worst-case backdrop: a pure white "sunny" video frame. The script uses the standard library only.

The checker was tested against WCAG reference values before it was used:

| Input | Expected | Got | Exit |
|---|---|---|---|
| `#777777` on `#FFFFFF`, text | fail (just under 4.5:1) | 4.48:1 FAIL | 1 |
| `#767676` on `#FFFFFF`, text | pass (the darkest grey that passes) | 4.54:1 PASS | 0 |
| `#000000` on `#FFFFFF` | 21:1 | 21.00:1 | 0 |
| no pairs | fail (an empty proof proves nothing) | `0/0 pairs pass` | 1 |
| unknown token reference | malformed | `MALFORMED: unknown token reference` | 2 |

**First run on the real tokens failed. That was a real finding:** a focus ring drawn directly against the green primary fill reached only 1.07:1. The fix is geometric, not a colour change. The ring is `outline: 3px` with `outline-offset: 2px`, and a 2px `box-shadow` halo in `focus-inner` fills the offset gap. The ring therefore touches only the halo and the page, never the fill. Those two pairs are proven below, and the pair that can never occur was removed (decision log, 2026-10-03).

**Command and result (2026-10-03):**

```
$ python3 docs/design/tools/contrast_check.py --markdown
55/55 pairs pass        (exit 0)
```

## 2. Contrast proof (generated; do not hand-edit, re-run the command)

| Theme | Use | Foreground | Background | Kind | Minimum | Ratio | Result |
|---|---|---|---|---|---|---|---|
| light | Body text on page | color.light.text `#14191F` | color.light.bg `#FFFFFF` | text | 4.5:1 | 17.67:1 | PASS |
| light | Body text on surface | color.light.text `#14191F` | color.light.surface `#F3F5F7` | text | 4.5:1 | 16.17:1 | PASS |
| light | Secondary text on page | color.light.text-secondary `#4D5763` | color.light.bg `#FFFFFF` | text | 4.5:1 | 7.35:1 | PASS |
| light | Secondary text on surface | color.light.text-secondary `#4D5763` | color.light.surface `#F3F5F7` | text | 4.5:1 | 6.72:1 | PASS |
| light | Button label on primary | color.light.on-primary `#FFFFFF` | color.light.primary `#0B6B4D` | text | 4.5:1 | 6.51:1 | PASS |
| light | Button label on primary-hover | color.light.on-primary `#FFFFFF` | color.light.primary-hover `#08573F` | text | 4.5:1 | 8.59:1 | PASS |
| light | Primary button boundary vs page | color.light.primary `#0B6B4D` | color.light.bg `#FFFFFF` | non-text | 3.0:1 | 6.51:1 | PASS |
| light | Primary button boundary vs surface | color.light.primary `#0B6B4D` | color.light.surface `#F3F5F7` | non-text | 3.0:1 | 5.96:1 | PASS |
| light | Link on page | color.light.link `#1A56B0` | color.light.bg `#FFFFFF` | text | 4.5:1 | 7.00:1 | PASS |
| light | Link on surface | color.light.link `#1A56B0` | color.light.surface `#F3F5F7` | text | 4.5:1 | 6.40:1 | PASS |
| light | Link on info banner | color.light.link `#1A56B0` | color.light.info-surface `#E8F0FC` | text | 4.5:1 | 6.10:1 | PASS |
| light | Visited link on page | color.light.link-visited `#5B3A9E` | color.light.bg `#FFFFFF` | text | 4.5:1 | 8.26:1 | PASS |
| light | Control border on page | color.light.border-control `#69737E` | color.light.bg `#FFFFFF` | non-text | 3.0:1 | 4.82:1 | PASS |
| light | Control border on surface | color.light.border-control `#69737E` | color.light.surface `#F3F5F7` | non-text | 3.0:1 | 4.41:1 | PASS |
| light | Focus ring on page | color.light.focus `#1A56B0` | color.light.bg `#FFFFFF` | non-text | 3.0:1 | 7.00:1 | PASS |
| light | Focus ring on surface | color.light.focus `#1A56B0` | color.light.surface `#F3F5F7` | non-text | 3.0:1 | 6.40:1 | PASS |
| light | Focus inner halo vs primary fill | color.light.focus-inner `#FFFFFF` | color.light.primary `#0B6B4D` | non-text | 3.0:1 | 6.51:1 | PASS |
| light | Focus ring vs its inner halo | color.light.focus `#1A56B0` | color.light.focus-inner `#FFFFFF` | non-text | 3.0:1 | 7.00:1 | PASS |
| light | Error text on page | color.light.error `#B3261E` | color.light.bg `#FFFFFF` | text | 4.5:1 | 6.54:1 | PASS |
| light | Error text on error tint | color.light.error `#B3261E` | color.light.error-surface `#FDECEA` | text | 4.5:1 | 5.72:1 | PASS |
| light | Error border on page | color.light.error `#B3261E` | color.light.bg `#FFFFFF` | non-text | 3.0:1 | 6.54:1 | PASS |
| light | Success text on page | color.light.success `#1B6E33` | color.light.bg `#FFFFFF` | text | 4.5:1 | 6.32:1 | PASS |
| light | Provisional/warning text on warning banner | color.light.warning-text `#7A4A00` | color.light.warning-surface `#FFF4DE` | text | 4.5:1 | 6.86:1 | PASS |
| light | Body text on warning banner | color.light.text `#14191F` | color.light.warning-surface `#FFF4DE` | text | 4.5:1 | 16.19:1 | PASS |
| light | Body text on info banner | color.light.text `#14191F` | color.light.info-surface `#E8F0FC` | text | 4.5:1 | 15.40:1 | PASS |
| light | Progress fill vs track background | color.light.primary `#0B6B4D` | color.light.bg `#FFFFFF` | non-text | 3.0:1 | 6.51:1 | PASS |
| light | Progress track outline vs page | color.light.progress-track `#69737E` | color.light.bg `#FFFFFF` | non-text | 3.0:1 | 4.82:1 | PASS |
| light | Text on scrim over a white video frame | color.light.on-scrim `#FFFFFF` | color.light.scrim `#000000A6` over `#FFFFFF` | text | 4.5:1 | 7.00:1 | PASS |
| dark | Body text on page | color.dark.text `#E9EDF1` | color.dark.bg `#0F1419` | text | 4.5:1 | 15.73:1 | PASS |
| dark | Body text on surface | color.dark.text `#E9EDF1` | color.dark.surface `#1B232B` | text | 4.5:1 | 13.50:1 | PASS |
| dark | Secondary text on page | color.dark.text-secondary `#A8B3BE` | color.dark.bg `#0F1419` | text | 4.5:1 | 8.69:1 | PASS |
| dark | Secondary text on surface | color.dark.text-secondary `#A8B3BE` | color.dark.surface `#1B232B` | text | 4.5:1 | 7.46:1 | PASS |
| dark | Button label on primary | color.dark.on-primary `#0F1419` | color.dark.primary `#4CC08C` | text | 4.5:1 | 8.13:1 | PASS |
| dark | Button label on primary-hover | color.dark.on-primary `#0F1419` | color.dark.primary-hover `#6BD3A2` | text | 4.5:1 | 10.11:1 | PASS |
| dark | Primary button boundary vs page | color.dark.primary `#4CC08C` | color.dark.bg `#0F1419` | non-text | 3.0:1 | 8.13:1 | PASS |
| dark | Primary button boundary vs surface | color.dark.primary `#4CC08C` | color.dark.surface `#1B232B` | non-text | 3.0:1 | 6.98:1 | PASS |
| dark | Link on page | color.dark.link `#8AB4F8` | color.dark.bg `#0F1419` | text | 4.5:1 | 8.78:1 | PASS |
| dark | Link on surface | color.dark.link `#8AB4F8` | color.dark.surface `#1B232B` | text | 4.5:1 | 7.54:1 | PASS |
| dark | Link on info banner | color.dark.link `#8AB4F8` | color.dark.info-surface `#16273F` | text | 4.5:1 | 7.14:1 | PASS |
| dark | Visited link on page | color.dark.link-visited `#C3A6F2` | color.dark.bg `#0F1419` | text | 4.5:1 | 8.87:1 | PASS |
| dark | Control border on page | color.dark.border-control `#7F8B97` | color.dark.bg `#0F1419` | non-text | 3.0:1 | 5.33:1 | PASS |
| dark | Control border on surface | color.dark.border-control `#7F8B97` | color.dark.surface `#1B232B` | non-text | 3.0:1 | 4.57:1 | PASS |
| dark | Focus ring on page | color.dark.focus `#8AB4F8` | color.dark.bg `#0F1419` | non-text | 3.0:1 | 8.78:1 | PASS |
| dark | Focus ring on surface | color.dark.focus `#8AB4F8` | color.dark.surface `#1B232B` | non-text | 3.0:1 | 7.54:1 | PASS |
| dark | Focus inner halo vs primary fill | color.dark.focus-inner `#0F1419` | color.dark.primary `#4CC08C` | non-text | 3.0:1 | 8.13:1 | PASS |
| dark | Focus ring vs its inner halo | color.dark.focus `#8AB4F8` | color.dark.focus-inner `#0F1419` | non-text | 3.0:1 | 8.78:1 | PASS |
| dark | Error text on page | color.dark.error `#FF8A80` | color.dark.bg `#0F1419` | text | 4.5:1 | 8.11:1 | PASS |
| dark | Error text on error tint | color.dark.error `#FF8A80` | color.dark.error-surface `#3A1A18` | text | 4.5:1 | 6.86:1 | PASS |
| dark | Success text on page | color.dark.success `#6FD08C` | color.dark.bg `#0F1419` | text | 4.5:1 | 9.76:1 | PASS |
| dark | Provisional/warning text on warning banner | color.dark.warning-text `#FFC966` | color.dark.warning-surface `#33270F` | text | 4.5:1 | 9.60:1 | PASS |
| dark | Body text on warning banner | color.dark.text `#E9EDF1` | color.dark.warning-surface `#33270F` | text | 4.5:1 | 12.41:1 | PASS |
| dark | Body text on info banner | color.dark.text `#E9EDF1` | color.dark.info-surface `#16273F` | text | 4.5:1 | 12.78:1 | PASS |
| dark | Progress fill vs page | color.dark.primary `#4CC08C` | color.dark.bg `#0F1419` | non-text | 3.0:1 | 8.13:1 | PASS |
| dark | Progress track outline vs page | color.dark.progress-track `#7F8B97` | color.dark.bg `#0F1419` | non-text | 3.0:1 | 5.33:1 | PASS |
| dark | Text on scrim over a white video frame | color.dark.on-scrim `#FFFFFF` | color.dark.scrim `#000000A6` over `#FFFFFF` | text | 4.5:1 | 7.00:1 | PASS |

## 3. Colour usage rules

1. **Text tokens** (`text`, `text-secondary`, `link`, `error`, `success`, `warning-text`) are only used on the backgrounds they are proven against above. A new combination needs a new `contrastPairs` row and a re-run.
2. **`border-subtle` is decorative only.** It is below 3:1 by design, so it must never be the only visible boundary of a control. Inputs, radios, checkboxes and secondary buttons use `border-control`, which is 2 px wide.
3. **Never colour alone** (NFR-034; NFR-A11Y-05). Errors carry the word "Error:" in the page title, the "There is a problem" summary and the message text [DPA/DESIGN-13]. Success carries an icon and words ("Video received"). Provisional states carry the word "provisional".
4. **Disabled controls that carry information keep full contrast.** WCAG exempts inactive components from contrast, but the "Rally scoring (provisional)" option and its reason "available once the rules are verified" are information the player must read (FR-043, ST-016). They use `text` / `warning-text` on `warning-surface`, with `aria-disabled="true"` and a visible reason, never a greyed-out label. No token below 4.5:1 exists for text, on purpose.
5. **Text over video always sits on `scrim`.** The 65% black scrim gives 7.00:1 for white text even over a pure white frame. That covers the worst case of NFR-029's "sunny" reference frame. The shaded and indoor frames are darker, so they cannot be worse for white text on a black scrim (judgment).
6. **Dark theme** follows `prefers-color-scheme`. Both themes are proven. A manual theme switch is out of scope for Sprint 1 (judgment).
7. Charts, heatmaps and court overlays (R1 Sprint 3+, R2) are **not** covered by v0.1. They need their own ramp, with 3:1 between adjacent marks or printed labels (DES FR-UX-73). This is planned for the score-sheet and dashboard design docs.

## 4. Type, space and size

| Token | Value | Rule |
|---|---|---|
| `font-family` | system stack | No web font on the first route, which keeps NFR-015's 200 KB budget |
| `size.sm` | 1rem (16 px) | Minimum for body text and inputs. This also stops iOS Safari from zooming on input focus (judgment) |
| `size.md` | 1.125rem (18 px) | Default body text: courtside, outdoors, at arm's length (judgment) |
| `size.lg` / `size.xl` | 24 / 32 px | Headings. 24 px regular counts as large text under SC 1.4.3, but we still hold all text to 4.5:1 |
| `line-height.body` | 1.5 | Text is in rem only, so it scales with browser zoom |
| `space.gutter-mobile` | 16 px | Side gutter from 320 to 767 CSS px |
| `space.content-max` | 40 rem | Question pages and long text |
| `size.target-min` | 24 px | Absolute floor for any pointer target, SC 2.5.8 [DPA/DESIGN-02]; NFR-028 |
| `size.target-touch` | 48 px | Primary controls, "Continue", radio and checkbox rows (whole row is the target), upload controls, "Change" links on the check-answers page [DPA/DESIGN-10] |
| `size.target-gap` | 8 px | Between adjacent touch targets (judgment) |
| `border.control-width` | 2 px | Control boundaries |
| `focus.*` | 3 px ring, 2 px offset, 2 px inner halo | Always on `:focus-visible`; never `outline: none` without a replacement |
| `focus.scroll-padding` | sticky height + 1 rem | `html { scroll-padding-top/bottom }`, so a focused element is never hidden behind the sticky upload bar or the error banner, SC 2.4.11 [DPA/DESIGN-07]; NFR-031 |
| `motion.reduced-motion` | 0 ms | Under `prefers-reduced-motion: reduce` (judgment: SC 2.3.3 is AAA and was not fetched) |
| `breakpoints.xs` | 320 px | Reflow floor; Playwright viewport matrix 320/360/768/1280 (NFR-034) |

## 5. What the front end must test (handed to senior-frontend-engineer and senior-qa-engineer)

- The contrast proof runs in CI. Suggested: the SRE adds `python3 docs/design/tools/contrast_check.py` as a docs job, so a token change cannot merge red. The designer does not edit CI (lane rule).
- The CSS variables generated from `tokens.json` equal the JSON values: one Vitest snapshot.
- axe-core on every page (NFR-027) covers rendered contrast. The target-size check (NFR-028) uses `size.target-min`.
