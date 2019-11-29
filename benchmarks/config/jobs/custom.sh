#!/bin/sh

prepare() {
  echo "Changing working directory to: $work_dir" ;
  cd "$work_dir" ;
  pwd ;
  printf "$(date) " ;
  printf "$(date) " ;
} ;
compute() {
  printf "$(date)" ;
  echo "Starting job" ;
  DIR_NAME=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 13 ; echo '') ;
  mkdir $DIR_NAME ;
  cd $DIR_NAME ;
  START_TIME="$(date)" ;
  for i in `seq 0 99`
  do
    touch file_${i}
  done ;
  END_TIME="$(date )"
  echo "$START_TIME" >> /results/compute_results ;
  echo "$END_TIME" >> /results/compute_results ;
  printf "$(date) " ;
  echo "sysbench compute end" ;

} ;
clean() {
  printf "$(date)" ;
  echo "Starting cleaning." ;

  printf "$(date) " ;
  echo "clean end" ;
} ;