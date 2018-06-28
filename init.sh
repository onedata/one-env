#!/usr/bin/env bash

git clone https://github.com/onedata/charts.git

cd charts
git checkout feature/luma
cd ..

git apply sources_patch.patch