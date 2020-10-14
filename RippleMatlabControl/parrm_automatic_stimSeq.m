%% Initializations
% Clean the world
close all; fclose('all'); clc; clear all;
% folderPath = 'C:\Users\Peep Sheep\Trellis\dataFiles\';
folderPath = 'F:\Trellis\';

% folderPath = 'C:\Users\Radu\Desktop\';
dateStr = datestr(now, 'yyyymmdd');
subFolderPath = sprintf('%s%s1300-Benchtop', folderPath, dateStr);
if ~isfolder(subFolderPath)
    mkdir(subFolderPath)
end
stimResLookup = [1, 2, 5, 10, 20];
% Manually set stimRes to the index of the current active stim resolution,
% from Trellis
% TODO: automate based on amplitude bounds
stimRes = 5;

% set to true if ripple system is disconnected, to dry run code
disableErrors = 0;
%%
% Initialize xippmex
status = xippmex;
try
    if status ~= 1; error('Xippmex Did Not Initialize');  end
catch ME
    if disableErrors
        disp(ME.message);
    else
        rethrow(ME);
    end
end
    
% Find all channels (they are both able to record & stim)-> size = 96
try
    Chans_analog = xippmex('elec', 'analog');
    % Chans = 1:96;
    Chans = xippmex('elec', 'nano');
    FEs = unique(ceil(Chans/32));
    FE_analog = unique(ceil(Chans_analog/32));
catch ME
    if disableErrors
        disp(ME.message);
    else
        rethrow(ME);
    end
end
%% Change Ripple indices to Paddle 24 indices
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
blockID = 1
% which bank is connected to which headstage determines to what channels
% correspond each electrode, please set this here :
A = 'x';
B = 'y';
% Headstage stored to C bank can potentially be doubled
C = 'z';
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% z assigned to C bank [electrodes 17-24 above 1.5mA]
if A == 'x' && B == 'y'&& C == 'z'
    Chans_paddle = [1, 2, 3, 4, 5 ,6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24];
    % do not use double channels
    Chans_paddle_to_ripple = {1, 3, 5, 7, 2, 4, 6, 8,    9, 11, 13, 15, 10, 12, 14, 16,    17, 19, 21, 23, 18, 20, 22, 24};
    % use double channels
    % Chans_paddle_to_ripple = {1, 3, 5, 7, 2, 4, 6, 8,    9, 11, 13, 15, 10, 12, 14, 16,    [17; 25], [19; 27], [21; 29], [23; 31], [18; 26], [20; 28], [22; 30], [24; 32]};
    % y assigned to C bank [electrodes 9-16 above 1.5 mA]
elseif A == 'z' && B == 'x' && C == 'y'
    Chans_paddle = [1, 2, 3, 4, 5 ,6, 7, 8,    9, 10, 11, 12, 13, 14, 15, 16,   17, 18, 19, 20, 21, 22, 23, 24];
    Chans_paddle_to_ripple = [9,11,13,15,10,12,14,16,  [17,25] , [19,27] , [21, 29] , [23, 31] , [18, 26] , [20, 28] , [22, 30] , [24, 32] , 1, 3, 5, 7, 2, 4, 6, 8];
    % Chans_paddle_to_ripple = [9,11,13,15,10,12,14,16,  [17,25] , [19,27] , [21, 29] , [23, 31] , [18, 26] , [20, 28] , [22, 30] , [24, 32] , 1, 3, 5, 7, 2, 4, 6, 8];
    % x assigned to C bank [electrodes 1-8 above 1.5 mA]
elseif A == 'y' && B == 'z' && C == 'x'
    Chans_paddle = [1, 2, 3, 4, 5 ,6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24];
    Chans_paddle_to_ripple = [ [17; 25] , [19; 27] , [21; 29] , [23; 31] , [18; 26] , [20; 28] , [22; 30] , [24; 32] ,     1, 3, 5, 7, 2, 4, 6, 8,       9, 11, 13, 15, 10, 12, 14, 16 ];
    % Chans_paddle_to_ripple = [ [17; 25] , [19; 27] , [21; 29] , [23; 31] , [18; 26] , [20; 28] , [22; 30] , [24; 32] ,     1, 3, 5, 7, 2, 4, 6, 8,       9, 11, 13, 15, 10, 12, 14, 16 ];
else
    sprintf('Error in assigning headstages, please change A, B and C assignments')
    return;
end

logFileName = sprintf('%s\\Block00%d_autoStimLog.json', subFolderPath, blockID);
% close out old log
prevLogFileName = sprintf('%s\\Block00%d_autoStimLog.json', subFolderPath, blockID-1);
if isfile(prevLogFileName)
    logFileID = fopen(prevLogFileName, 'a');
    fprintf(logFileID, ']');
    fclose(logFileID);
end
% check if already exists
if isfile(logFileName)
    error('log file already exists');
end

logFileID = fopen(logFileName, 'a');
fprintf(logFileID, '[');
fclose(logFileID);
% flag to control json file structure
firstBlockEntry = 1;
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Stimulation Settings

% 1. Stimulation signal settings [variable/randomly chosen]
m = input(sprintf('Writing to log %d Do you want to continue, Y/N [Y]:', blockID),'s');
if m=='N'
	error('Trial aborted')
end
% Cathode/Anode setting
whichNanoProbe = 1;
% 1 caudal 2 rostral
cathode_list = [21];
anode_list = [];
%
whichNanoBlock = 2;
block_cathode_list = [1, 9, 13, 20];
block_anode_list = [];
block_FR = 1000;
block_amp = 900;
block_TL = 2000;
block_PD = 0.033;
block_PR = 1;
block_params = [block_FR, block_amp, block_TL, block_PD, block_PR];
blockFreqMultiplier = 10;
nBlockBurnIn = 60;
% 
% stimProtocol = 'manual';
stimProtocol = 'sweep';
% % % % % % %
minAmp = 60;
maxAmp = 900;

% % % % % % %
% Sweep
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if strcmp(stimProtocol, 'sweep')
    frequencies_Hz = [10.2, 25.2, 50.2, 100.2];
    nominalAmplitudeSteps_uA = linspace(minAmp, maxAmp, 7);
    % How many times to repeat the train
    repetition = 5;
    % Number of combination array's copy
    comb_copies = 3;
    phaseRatio = 3;
    % repeat the waveform frequencyMultiplier times to achieve
    % rates higher than 1000 Hz
    frequencyMultiplier = 1;
    trainLength_ms = 300;
    phaseDuration_ms = 0.150;
    % Train interval (s)
    TI = block_TL / 1000 + .15;
    % Combination interval (s) - extra pause between combinations
    CI = 0;
elseif strcmp(stimProtocol, 'manual')
    frequencies_Hz = [100];
    nominalAmplitudeSteps_uA = [maxAmp];
    frequencyMultiplier = 1;
    % How many times to repeat the train
    repetition = 1;
    % Number of combination array's copy
    comb_copies = 1;
    %
    phaseRatio = 3;
    trainLength_ms = 300;
    phaseDuration_ms = 0.150;
    % Train interval (s)
    TI = block_TL / 1000;
    CI = 0;
end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Filter timeseries 'data' using PARRM
% Assume 'data' has a 200Hz sampling rate and 150Hz stimulation frequency
guessPeriod=30000/(block_FR * blockFreqMultiplier); % Theoretical stimulation period
span=[2000,12000]; % Span of samples in 'data' where artifact is regular
windowSize=200; % Width of window in sample space to be used for removal
skipSize=20; % Number of samples to ignore in sample space
windowDirection='both'; % Remove using information from the past and future

%Period=FindPeriodLFP(data,span,guessPeriod); % Find the period of stimulation in 'data'
Period=guessPeriod;
periodDist=Period/700; % Window in period space for which samples will be averaged

PARRM=PeriodicFilter(Period,windowSize,periodDist,skipSize,windowDirection); % Create the linear filter

[Freq, Amp] = meshgrid(frequencies_Hz, nominalAmplitudeSteps_uA);
c = cat(2, Freq', Amp');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% To reach 50 repetition per combination, one way is to :
% 1. Generate a combination array (25x2)
% 2. Randomly pick a row in the array (i.e a combination)
% 3. Stimulate with 10 repeats of that combination
% 4. Discard the row
% 5. Repeat 2. 3. and 4. until the comb array is empty
% 6. Repeat all the previous steps 5 times to reach 50 repeats
% per combination randomly ordered in time

thisPaddleToRippleLookupProbe = Chans_paddle_to_ripple;
for i=1:size(thisPaddleToRippleLookupProbe, 2)
    thisPaddleToRippleLookupProbe{i} = thisPaddleToRippleLookupProbe{i} + (whichNanoProbe-1) * 32;
end
thisPaddleToRippleLookupBlock = Chans_paddle_to_ripple;
for i=1:size(thisPaddleToRippleLookupBlock, 2)
    thisPaddleToRippleLookupBlock{i} = thisPaddleToRippleLookupBlock{i} + (whichNanoBlock-1) * 32;
end
% Execute Stim
% Iterates over combination array copies
clc
logFileID = fopen(logFileName, 'a');
% Turn off any ongoing stim
% try
%     xippmex('stim', 'enable', 0);
%     xippmex('stim', 'res', Chans, [stimRes]);
%     xippmex('stim', 'enable', stimElectrodes);
% catch ME
%     if disableErrors
%         disp(ME.message);
%     else
%         rethrow(ME);
%     end
% end
for co=1:nBlockBurnIn
    % Function call to stimulate
    [blockCmd, blockElectrodes] = high_res_stim_command_builder_stimSeq(...
        block_cathode_list, block_anode_list, thisPaddleToRippleLookupBlock,...
        block_params, stimResLookup(stimRes), blockFreqMultiplier);
    try
        stimNIPTime = xippmex('time');
        currStimRes = xippmex('stim', 'res', blockElectrodes);
        xippmex('stimseq', blockCmd);
        saveStim = jsonencode(struct(...
            'stimCmd', blockCmd, 't', cast(stimNIPTime, 'int64'),...
            'stimRes', currStimRes, 'frequencyMultiplier', frequencyMultiplier, 'blockFreqMultiplier', blockFreqMultiplier));
        % Save to log
        if ~firstBlockEntry
            fprintf(logFileID, ', ');
        end
        firstBlockEntry = 0;
        fprintf(logFileID, '%s', saveStim);
    catch ME
        if disableErrors
            disp(ME.message);
        else
            rethrow(ME);
        end
      end
    pause(TI);
    % data = xippmex('cont', 1, 200, 'raw', stimNIPTime)';
    data = xippmex('cont', 1, TI * 1000, 'raw', stimNIPTime - 500*30)';
    Filtered=((filter2(PARRM.',data,'same')-data)./(1-filter2(PARRM.',ones(size(data)),'same'))+data)';
    plot(data);
    hold on
    plot(Filtered);
    legend('original', 'filtered')
%     % Train Interval
%     refT = tic;
%     elapsedT = toc(refT);
%     while elapsedT < TI
%         % disp(elapsedT);
%         elapsedT = toc(refT);
%         if xippmex('stim', 'enable') == 0
%             break
%         end
%     end
end

try
    [blockCmd, blockElectrodes] = high_res_stim_command_builder_stimSeq(...
        block_cathode_list, block_anode_list, thisPaddleToRippleLookupBlock,...
        block_params, stimResLookup(stimRes), blockFreqMultiplier);
    for i=1:comb_copies
        comb_array = reshape(c, [], 2);
        comb_array_length = size(comb_array, 1);
        % tic;
        % Iterate over each combination inside the i-th combination array
        for j=1:comb_array_length
            % fprintf('Combination %d / %d\n', [(i-1)*comb_array_length + j,comb_array_length*comb_copies])
            % Randomization in the comb list
            rd_idx = randperm(size(comb_array, 1), 1);
            randomizedParamList = comb_array(rd_idx, :);
            % Add constant parameters
            randomizedParamList = [randomizedParamList, trainLength_ms, phaseDuration_ms, phaseRatio];
            fprintf('\nStim: amplitude %4.2f uA, rate %4.2f Hz\n', randomizedParamList(2), randomizedParamList(1));
            % Delete than comb from the list
            comb_array(rd_idx, :) = [];
            % # repetition of each combination; e.g. 3 times
            % tic;
            for k=1:repetition
                % Function call to stimulate
                [stimCmd, stimElectrodes] = high_res_stim_command_builder_stimSeq(...
                    cathode_list, anode_list, thisPaddleToRippleLookupProbe,...
                    randomizedParamList, stimResLookup(stimRes), frequencyMultiplier);
                % Stim time is roughly 0.5 ms -> negligeable
                concatenatedCmd = [blockCmd, stimCmd];
                allActiveElectrodes = [blockElectrodes, stimElectrodes];
                try
                    stimNIPTime = xippmex('time');
                    currStimRes = xippmex('stim', 'res', allActiveElectrodes);
                    xippmex('stimseq', concatenatedCmd);
                    saveStim = jsonencode(struct(...
                        'stimCmd', concatenatedCmd, 't', cast(stimNIPTime, 'int64'),...
                        'stimRes', currStimRes, 'frequencyMultiplier', frequencyMultiplier, 'blockFreqMultiplier', blockFreqMultiplier));
                    % Save to log
                    if ~firstBlockEntry
                        fprintf(logFileID, ', ');
                    end
                    firstBlockEntry = 0;
                    fprintf(logFileID, '%s', saveStim);
                catch ME
                    if disableErrors
                        disp(ME.message);
                    else
                        rethrow(ME);
                    end
                end
%                 % Train Interval
%                 refT = tic;
%                 elapsedT = toc(refT);
%                 while elapsedT < TI
%                     % disp(elapsedT);
%                     elapsedT = toc(refT);
%                     if xippmex('stim', 'enable') == 0
%                         break
%                     end
%                 end
                pause(TI)
                %%%%% RD 04-24-2020 Don't think this is necessary
                % Enable stimulation for cathodes and anodes selected previously
                try
                    % xippmex('stim', 'enable', 0);
                    % xippmex('stim', 'res', stimElectrodes, [3]);
                    % xippmex('stim', 'enable', stimElectrodes);
                    % m = input(sprintf('Writing to log %d Do you want to continue, Y/N [Y]:', blockID),'s');
                catch ME
                    if disableErrors
                        disp(ME.message);
                    else
                        rethrow(ME);
                    end
                end
                % %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
                % fprintf('\nExecuting\n%s\n', saveStim);
            end
            % toc;
            % pause in between combinations
            pause(CI);
        end
        % toc;
    end
catch ME
%     try
%         xippmex('stim', 'enable', 0);
%         xippmex('stim', 'res', Chans, [stimRes]);
%     catch ME
%         if disableErrors
%             disp(ME.message);
%         else
%             rethrow(ME);
%         end
%     end
if disableErrors
    disp(ME.message);
else
    rethrow(ME);
end
end
fclose(logFileID);
fprintf('\nRun complete!\n');
% toc;
%%