%% Initializations
% Clean the world
close all; fclose('all'); clc; clear all;
folderPath = 'C:\Users\Peep Sheep\Trellis\dataFiles\';
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

% Get NIP clock time right before turning streams on (30 kHz sampling) recChans
% set stimulation resolution:
% try
%     xippmex('stim', 'enable', 0);
%     xippmex('stim', 'res', Chans, [stimRes]);
%     xippmex('stim', 'enable', Chans);
% catch ME
%     if disableErrors
%         disp(ME.message);
%     else
%         rethrow(ME);
%     end
% end

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
if A == 'x' && B == 'y' && C == 'z'
    Chans_paddle = [1, 2, 3, 4, 5 ,6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24];
    Chans_paddle_to_ripple = {1, 3, 5, 7, 2, 4, 6, 8,    9, 11, 13, 15, 10, 12, 14, 16,    [17; 25], [19; 27], [21; 29], [23; 31], [18; 26], [20; 28], [22; 30], [24; 32]};
    % y assigned to C bank [electrodes 9-16 above 1.5 mA]
elseif A == 'z' && B == 'x' && C == 'y'
    Chans_paddle = [1, 2, 3, 4, 5 ,6, 7, 8,    9, 10, 11, 12, 13, 14, 15, 16,   17, 18, 19, 20, 21, 22, 23, 24];
    Chans_paddle_to_ripple = [9,11,13,15,10,12,14,16,  [17,25] , [19,27] , [21, 29] , [23, 31] , [18, 26] , [20, 28] , [22, 30] , [24, 32] , 1, 3, 5, 7, 2, 4, 6, 8];
    % x assigned to C bank [electrodes 1-8 above 1.5 mA]
elseif A == 'y' && B == 'z' && C == 'x'
    Chans_paddle = [1, 2, 3, 4, 5 ,6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24];
    Chans_paddle_to_ripple = [ [17; 25] , [19; 27] , [21; 29] , [23; 31] , [18; 26] , [20; 28] , [22; 30] , [24; 32] ,     1, 3, 5, 7, 2, 4, 6, 8,       9, 11, 13, 15, 10, 12, 14, 16 ];
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
whichNano = 1;
% 1 caudal 2 rostral
cathode_list = [11];
anode_list = [];

% stimProtocol = 'manual';
% stimProtocol = 'diagnostic';
% stimProtocol = 'sweep';
stimProtocol = 'continuous';
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
    repetition = 3;
    % Number of combination array's copy
    comb_copies = 5;
    % phase raatio is the aspect ratio of biphasic pulses, where 1 is the
    % phaseDuration (in msec) of the first phase, and the second phase is
    % phaseRatio times longer.
    phaseRatio = 3;
    % duration of the train of pulses
    trainLength_ms = 300;
    % duration of the first phase of the biphasic waveform
    phaseDuration_ms = 0.150;
    % Train interval between successive pulse trains (sec)
    TI = 0.7 + trainLength_ms / 1000;
    CI = 0;
elseif strcmp(stimProtocol, 'continuous')
    % frequencies_Hz = [50, 100, 1000, 10000];
    % frequencies_Hz = [10, 50, 100, 1000];
    frequencies_Hz = [1000];
    % frequencies_Hz = [100.2];
    nominalAmplitudeSteps_uA = linspace(minAmp, maxAmp, 5);
    % How many times to repeat the train
    repetition = 30;
    % Number of combination array's copy
    comb_copies = 1;
    phaseRatio = 1;
    % repeat the waveform frequencyMultiplier times to achieve
    % rates higher than 1000 Hz
    frequencyMultiplier = 10;
    trainLength_ms = 4000;
    phaseDuration_ms = 0.033;
    % Train interval (s)
    TI = 0.5 * trainLength_ms / 1000;
    % Combination interval (s) - extra pause between combinations
    CI = 120;
    % Single
elseif strcmp(stimProtocol, 'diagnostic')
    % frequencies_Hz = [10.2, 25.2, 50.2, 100.2];
    frequencies_Hz = [100.2];
    nominalAmplitudeSteps_uA = linspace(minAmp, maxAmp, 3);
    % How many times to repeat the train
    repetition = 1;
    % Number of combination array's copy
    comb_copies = 3;
    phaseRatio = 3;
    trainLength_ms = 300;
    phaseDuration_ms = 0.150;
    % Train interval (s)
    TI = 2.7 + trainLength_ms / 1000;
    CI = 0;
    % Single
elseif strcmp(stimProtocol, 'manual')
    frequencies_Hz = [100];
    nominalAmplitudeSteps_uA = [maxAmp];
    % How many times to repeat the train
    repetition = 1;
    % Number of combination array's copy
    comb_copies = 1;
    %
    phaseRatio = 3;
    trainLength_ms = 300;
    phaseDuration_ms = 0.150;
    % Train interval (s)
    TI = 0.7 + trainLength_ms / 1000;
    CI = 0;
end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

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

thisPaddleToRippleLookup = Chans_paddle_to_ripple;
for i=1:size(thisPaddleToRippleLookup, 2)
    thisPaddleToRippleLookup{i} = thisPaddleToRippleLookup{i} + (whichNano-1) * 32;
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
try
    for i=1:comb_copies
        comb_array = reshape(c, [], 2);
        comb_array_length = size(comb_array, 1);
        tic;
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
                    cathode_list, anode_list, thisPaddleToRippleLookup,...
                    randomizedParamList, stimResLookup(stimRes), frequencyMultiplier);
                % Stim time is roughly 0.5 ms -> negligeable
                try
                    stimNIPTime = xippmex('time');
                    currStimRes = xippmex('stim', 'res', stimElectrodes);
                    xippmex('stimseq', stimCmd);
                    saveStim = jsonencode(struct(...
                        'stimCmd', stimCmd, 't', cast(stimNIPTime, 'int64'),...
                        'stimRes', currStimRes, 'frequencyMultiplier', frequencyMultiplier));
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
                %%%%% RD 04-24-2020 Don't think this is necessary
                % Enable stimulation for cathodes and anodes selected previously
                try
                    xippmex('stim', 'enable', 0);
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
                % Train Interval
                pause(TI)
            end
            % toc;
            % pause in between combinations
            pause(CI);
        end
        toc;
    end
catch
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