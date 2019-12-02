Directory containing configurations for benchmarks. Benchmark is a tool that 
allows to perform script defined by the user on multiple Oneclient pods 
simultaneously. \
\
Each benchmark consists of one or many suites. Each suite consists of one or 
many jobs. Each job comprise of 3 stages, defined as bash functions with 
respective names:
* prepare
* compute
* clean  

All Oneclients are synchronized before each stage of the job (i.e. all 
Oneclients have to end current stage and notify other Oneclients to proceed 
to the next stage). \
\
Benchmark tool is capable of logging counters from Oneclient to Grafana. It 
also generates test reports, that are later published to github repository 
(for now all reports are published to this repository 
https://github.com/groundnuty/reports/tree/master/orzech-dev) \
\
NOTE: In order to make it possible for benchmark to log counters to Grafana and 
publish reports to github repository it is necessary to provide:  
* Grafana API key
* Grafana password
* ssh key to github repository

Place them in appropriate files placed in benchmarks/config/private directory.