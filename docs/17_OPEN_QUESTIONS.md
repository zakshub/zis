# Open Questions

These questions are intentionally deferred until the relevant milestone. They are not blockers for documentation foundation.

## Runtime

1. What language should own the classical core runtime?
2. Is Python the best first implementation or should the core be split between a small portable kernel and a modern service layer?
3. Which durable data export formats become mandatory?

## Memory

1. What confidence scale should be canonical?
2. What decay rules should apply to preferences versus factual evidence?
3. What evidence volume triggers consolidation?

## Observation

1. Which source is the first real connector?
2. Which data categories are never allowed into durable memory?
3. What default retention period applies to raw observations?

## Specialist federation

1. Should specialists be invoked through local CLI, HTTP, repository contracts or multiple adapters?
2. How should version compatibility be negotiated?
3. What is the fallback when a specialist is unavailable?

## Simulation world

1. 2D, 2.5D or 3D first?
2. Browser renderer or native renderer?
3. How many creature states are needed for useful visualization?
4. Which backend events deserve visible world animation?

## Product future

1. Will ZIS always remain single owner, or will isolated instances later become a product?
2. If productized, what parts remain private intellectual property versus public specification?