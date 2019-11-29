apk update; apk add bash;
prepare() {
  echo "Changing working directory to: $work_dir" ;
  cd "$work_dir" ;
  pwd ;
  printf "$(date) " ; echo "Starting ioping prep with truncate." ;
  eval truncate $env_prepare_args ;
  printf "$(date) " ; echo "ioping prep end" ;
} ;
compute() {
  printf "$(date)" ; echo "Starting computation sysbench run." ;
  bash -c 'eval ioping $0 | tee >(sed -ne "/ioping statistics/,$ p" > /results/compute_results)' "$env_compute_args" ;
  printf "$(date) " ; echo "sysbench compute end" ;
} ;
clean() {
  printf "$(date)" ; echo "Starting cleaning." ;
  echo "No cleaning needed." ;
  printf "$(date) " ; echo "clean end" ;
} ;