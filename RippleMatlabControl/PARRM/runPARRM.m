% Filter timeseries 'data' using PARRM
% Assume 'data' has a 200Hz sampling rate and 150Hz stimulation frequency
guessPeriod=30000/10000; % Theoretical stimulation period
span=[2000,12000]; % Span of samples in 'data' where artifact is regular
windowSize=20000; % Width of window in sample space to be used for removal
skipSize=20; % Number of samples to ignore in sample space
windowDirection='both'; % Remove using information from the past and future

%Period=FindPeriodLFP(data,span,guessPeriod); % Find the period of stimulation in 'data'
Period=guessPeriod;
periodDist=Period/700; % Window in period space for which samples will be averaged

PARRM=PeriodicFilter(Period,windowSize,periodDist,skipSize,windowDirection); % Create the linear filter
Filtered=((filter2(PARRM.',data,'same')-data)./(1-filter2(PARRM.',ones(size(data)),'same'))+data)'; % Filter using the linear filter and remove edge effects