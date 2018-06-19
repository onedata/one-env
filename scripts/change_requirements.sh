#!/usr/bin/env bash

while read f ; do
  while read l ; do
    sed  -i '/- name: '$l'/,/repository/{s#\(repository:\).*#\1 file://../../charts/'$l'#}'  $f ;
  done < <(sed -n 's/- name: \(.*\)/\1/p' $f)
done < <(find . -name requirements.yaml)
