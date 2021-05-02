#!/bin/bash
for elems in {330000..3300000..330000}; do
    mkdir -p $(pwd)/muelu/ratio_10/ele_${elems}
    scp blue07:/home/ryan/wdir/input_files/beam_study_10M/muelu/ratio_10/ele_${elems}/beam_ratio_10_ele_${elems}.txt $(pwd)/muelu/ratio_10/ele_${elems}/beam_ratio_10_ele_${elems}.txt
done

