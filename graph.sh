#!/bin/bash

rm -rf graphs-$1
mkdir graphs-$1

for path in ./result/*; do
    [ -d "${path}" ] || continue # if not a directory, skip
    dirname="$(basename "${path}")"
    mkdir graphs-$1/$dirname
    rx=$(find ./result/$dirname -name '*rx.data')
    echo $rx
    for f in ./result/$dirname/*; do
        fname=$(basename $f)
        if [[ $f == *"cpu"* ]]
        then
            if [ ! -z "$rx" ]; then
                rate1=$(cut -d " " -f2 $rx | tail -1)
                rate2=$(cut -d " " -f3 $rx | tail -1)
                rate3=$(cut -d " " -f4 $rx | tail -1)
            else
                rate1=""
                rate2=""
                rate3=""
            fi
            gnuplot << EOF
                set xlabel "Time(s)"
                set ylabel "CPU"
                set term png
                set output "graphs-$1/$dirname/${fname}.png"
                plot '$f' using 1:2 title 'rx: $rate1' with lines, '$f' using 1:3 title 'rx: $rate2' with lines, '$f' using 1:4 title 'rx: $rate3' with lines
EOF
        fi
        if [[ $f == *"rx"* ]]
        then
        gnuplot << EOF
            set xlabel "Time(s)"
            set ylabel "Rx"
            set term png
            set output "graphs-$1/$dirname/${fname}.png"
            plot '$f' using 1:2 title '' with lines, '$f' using 1:3 title '' with lines, '$f' using 1:4 title '' with lines
EOF
        fi
        if [[ $f == *"tx"* ]]
        then
        gnuplot << EOF
            set xlabel "Time(s)"
            set ylabel "Tx"
            set term png
            set output "graphs-$1/$dirname/${fname}.png"
            plot '$f' using 1:2 title '' with lines, '$f' using 1:3 title '' with lines, '$f' using 1:4 title '' with lines
EOF
        fi

    done
done

