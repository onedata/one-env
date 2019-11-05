prepare() {
  echo "env_foo=$env_foo" ;
  echo "env_accessTokenld=$env_accessTokenld" ;
  echo "Changing working directory to: $work_dir" ;
  cd "$work_dir" ;
  pwd ;
  printf "$(date) " ; echo "Starting sysbench prep." ;
  eval sysbench $env_prepare_args ;
  printf "$(date) " ; echo "sysbench prep end" ;
} ;
compute() {
  echo "env_bar=$env_bar" ;
  printf "$(date) " ; echo "Starting computation sysbench run." ;
  bash -c 'sysbench $0 | tee >(sed -ne "/File operations/,$ p" > /results/compute_results)' "$env_compute_args" ;
  printf "$(date) " ; echo "sysbench compute end" ;
} ;
clean() {
  printf "$(date) " ; echo "Starting cleaning." ;
  echo "No cleaning needed." ;
  printf "$(date) " ; echo "clean end" ;
} ;