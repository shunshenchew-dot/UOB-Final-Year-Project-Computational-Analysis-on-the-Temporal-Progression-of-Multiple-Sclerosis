# Brain region filling and lesion overlap pipeline (ISBI 2015)

These scripts take the ISBI 2015 MRI scans (19 patients, 82 scans) to regional brain volumes and regional lesion volumes.

- Training cohort: SUBJ1–5, manual lesion masks from two raters.
- Test cohort: SUBJ6–19, lesion masks predicted by the CNN in Steps 4 and 5.
- 10 regions: basal ganglia, cerebellum, brainstem, ventricular system, white matter, frontal, parietal, temporal and occipital lobes, insular and cingulate cortex.

## Steps

| Step | Script | Purpose | Main outputs (per scan folder) |
|---|---|---|---|
| 0 | *3D Slicer (no script)* | Whole-brain parcellation (SlicerParcellation) | `Segmentation.seg.nrrd`, `label_legend.txt` |
| 1 | `Step 1: Macro-region Grouping.py` | Groups the parcellation labels into the 10 regions | `macro10.seg.nrrd`, `macro10_grouping.xlsx` |
| 2 | `Step 2: Voronoi Gap Filling Algorithm.py` | Fills unlabelled voxels inside the brain with the nearest region label | `macro_T1space_filled.nii.gz`, `comprehensive_report.txt` |
| 3 | `Step 3: Brain Volume Alignment Script.py` | Aligns the region map to the preprocessed T1, fills lesions and internal holes, computes regional volumes | `final_form.nii.gz`, `alignment_qc.png`, `lesion_region_report.txt`; volume CSVs in `ROOT` |
| 4 | `Step 4_ … (Expert Marker 1).py` | Trains the 2.5D Tiramisu CNN on Rater 1 masks and predicts test-cohort lesions | `testing_XX_YY_pred_isbi_focal_mask1.nii` |
| 5 | `Step 5_ … (Expert Marker 2).py` | Same as Step 4, for Rater 2 | `testing_XX_YY_pred_isbi_focal_mask2.nii` |
| 6 | `Step 6: Lesion Overlap Analysis Statistics.py` | Lesion volume in each region, per scan and rater; longitudinal summaries | CSVs and figures in `ROOT/Answers/` |

Run order: 0 → 1 → 2 → 3, and 4 → 5 (the two chains are independent). Then place the lesion masks in the scan folders (see Known issues 2) and run Step 6.

Before running, edit the hard-coded `ROOT` / `WORK_DIR` path at the top of each script. It currently points to `C:\Users\chews\…`.

## CNN (Steps 4–5)

Steps 4 and 5 need the LesionSeg repository: Zhang et al., 2019, https://github.com/HuahongZhang/LesionSeg. When they run, both scripts edit the repository themselves:
- worker count in `train.py` and `test.py`
- 12 input channels in `models/tiramisu_model.py`
- `configurations.py`, rewritten for each rater

The run behind the results also used the four patched files in `LesionSeg_patched_files/`. No Step applies these, so copy them over the matching repository files before running Step 4:

| File | Change |
|---|---|
| `data/ms_dataset.py` | Pads slices to a square size (the same change `patch_ms_dataset.py` makes) |
| `models/ms_model.py` | Casts input tensors to float32 |
| `util/image_property.py` | Clamps the slice index instead of failing an assert |
| `util/visualizer.py` | Makes visdom optional (Step 5 does this itself; Step 4 does not) |

## Requirements

- Python 3.10+ with `numpy`, `pandas`, `scipy`, `SimpleITK`, `nibabel`, `scikit-image`, `matplotlib`, `openpyxl`.
- Steps 4–5 also need an NVIDIA GPU with CUDA, plus `torch`, `torchvision`, `statsmodels` and `dominate`.

## Known issues

1. **Step 1, non-ventricular CSF.** `classify_to_macro10()` assigns non-ventricular CSF to the ventricular system. This inflated SUBJ11 Time 2 and SUBJ12 Time 3, which were corrected in the final dataset. Labels that match no keyword fall back to insular and cingulate cortex.
2. **Lesion masks into scan folders.** No script creates the `PatientXSyV1/V2Lesion_aligned_to_OrigT1.nii.gz` / `…Lesion.seg.nrrd` files, or converts the CNN predictions into per-scan lesion files. This was probably done by hand in 3D Slicer.
3. **Step 3 → Step 6 filename.** Step 6 looks for `resampled_fill.nii*`, but Step 3 writes `final_form.nii.gz`. Rename that file, or edit `find_macro()` in Step 6.
4. **Filenames.** The colons and the `2 (1).5D` text in the Step names come from a download artefact. Colons are not valid on Windows.

## Reference

Zhang, H., et al., Multiple sclerosis lesion segmentation with Tiramisu and 2.5D stacked slices. MICCAI 2019, LNCS 11766, 2019: p. 338–346.
