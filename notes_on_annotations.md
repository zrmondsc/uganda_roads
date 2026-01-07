# Notes on Road Annotations

This is a working document that I use to record the decision-making process for creating road annotations for road extraction from Maxar imagery. The goal here is to minimize the burden of creating the annotations while preserving some flexibility for different downstream modelling possibilities. 

---

## Annotation Objectives

Primary task:
- Detect linear transportation corridors (roads, tracks, footpaths)

The annotation strategy prioritizes:
- Geometric consistency
- Low human effort
- Robust learning for thin, heterogeneous features

---