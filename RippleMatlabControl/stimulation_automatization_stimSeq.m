%% Initializations 
% Clean the world
close all; fclose('all'); clc; clear all;
% folderPath = 'C:\Users\Peep Sheep\Trellis\dataFiles\';
folderPath = 'C:\Users\Radu\Documents\GitHub\matlabController\';
oldLogFileName = '';
stimResLookup = [1, 2, 5, 10, 20];
%%
% Initialize xippmex
status = xippmex;
if status ~= 1; error('Xippmex Did Not Initialize');  end

% Find all channels (they are both able to record & stim)-> size = 96
Chans_analog = xippmex('elec', 'analog');
% Chans = 1:64;
Chans = xippmex('elec', 'nano');
FEs = unique(ceil(Chans/32));
FE_analog = unique(ceil(Chans_analog/32));

% Get NIP clock time right before turning streams on (30 kHz sampling) recChans
timeZero = xippmex('time');

%% Change Ripple indices to Paddle 24 indices

dateStr = datestr(now, 'yyyymmdd');
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
blockID = sprintf('Block00%d', 1);
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
logFileName = sprintf('%s%s1200-Peep/%s_autoStimLog.json', folderPath, dateStr, blockID);
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if ~isempty(oldLogFileName)
    oldLogFileID = fopen(oldLogFileName, 'a');
    fprintf(oldLogFileID, '{}]');
    fclose(oldLogFileID);
end
oldLogFileName = logFileName;
logFileID = fopen(logFileName, 'a');
fprintf(logFileID, '[');
fclose(logFileID);

% which bank is connected to which headstage determines to what channels
% correspond each electrode, please set this here :
A = 'x';
B = 'y';
% Headstage stored to C bank can potentially be doubled
C = 'z';

% z assigned to C bank [electrodes 17-24 above 1.5mA]
if A == 'x' && B == 'y'&& C == 'z'
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
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% set stimulation resolution:
stimRes = 4;
try
    xippmex('stim', 'res', Chans, stimRes)
    xippmex('stim', 'enable');
catch ME
    fprintf(ME.message)
end
%% Stimulation Settings 

% 1. Stimulation signal settings [variable/randomly chosen]

% Cathode/Anode setting
whichNano = 2;
% 1 caudal 2 rostral
cathode_list = [];
anode_list = [10, 14, 9, 13];

% frequencies_Hz = [30, 50, 100, 200, 300];
frequencies_Hz = [10, 25, 50, 100];
% frequencies_Hz = [100];
% 40 corresponds to 20muA* 40 = 1000 microamps 
% phaseAmplitude_steps  = [400, 800, 1500, 2000, 3000] ./20;
% values divisible by 6
% 60   120   180   240   300   360   420   480   540   600   660   720   780   840   900   960
phaseRatio = 3;
if isempty(anode_list) || isempty(cathode_list)
    electrodeRatio = 1;
else
    electrodeRatio = floor(max(length(anode_list), length(cathode_list)) / min(length(anode_list), length(cathode_list)));
end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
nominalAmplitudeSteps_uA = linspace(60, 3960, 7);
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
phaseAmplitude_steps  = floor(nominalAmplitudeSteps_uA ./...
    (phaseRatio * electrodeRatio)) * (phaseRatio * electrodeRatio)...
    ./ stimResLookup(stimRes);

% 2. Stimulation signal settings [constant]
% get balanced freq and amp distribution 
% the only randomized parameter will be the order in which pre-defined
% combination of freq and amp are executed
[Freq, Amp] = meshgrid(frequencies_Hz, phaseAmplitude_steps);
c = cat(2, Freq', Amp');

% trainLength_ms  = 30 * 1000;
trainLength_ms = 300;
phaseDuration_ms = 0.150;
% Train interval (s)
TI = 0.7 + trainLength_ms / 1000;
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% How many times to repeat the train
repetition = 3;
% Number of combination array's copy
comb_copies = 5;
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% To reach 50 repetition per combination, one way is to :
% 1. Generate a combination array (25x2)
% 2. Randomly pick a row in the array (i.e a combination)
% 3. Stimulate with 10 repeats of that combination
% 4. Discard the row
% 5. Repeat 2. 3. and 4. until the comb array is empty
% 6. Repeat all the previous steps 5 times to reach 50 repeats
% per combination randomly ordered in time 

%
thisPaddleToRippleLookup = Chans_paddle_to_ripple;
for i=1:size(thisPaddleToRippleLookup, 2)
    thisPaddleToRippleLookup{i} = thisPaddleToRippleLookup{i} + (whichNano-1) * 32;
end
% Execute Stim
% Iterates over combination array copies
clc
logFileID = fopen(logFileName, 'a');
fprintf(logFileID, '[');
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
        % Delete than comb from the list
        comb_array(rd_idx, :) = [];
        % # repetition of each combination; e.g. 3 times
        % tic;
        for k=1:repetition
            % Function call to stimulate
            [stimCmd, stimElectrodes] = stim_elec_combination_stimSeq(...
                cathode_list, anode_list, thisPaddleToRippleLookup,...
                randomizedParamList, stimResLookup(stimRes));
%             %%%%% RD 04-24-2020 Don't think this is necessary
%             % Enable stimulation for cathodes and anodes selected previously
%             try
%                 xippmex('stim', 'enable', stimElectrodes);
%             catch
%                 fprintf(ME.message)
%             end
            % Stim time is roughly 0.5 ms -> negligeable
            try
                stimNIPTime = xippmex('time');
                xippmex('stimseq', stimCmd);
            catch ME
                fprintf(ME.message)
                stimNIPTime = cputime;
            end
            saveStim = jsonencode(struct(...
                'stimCmd', stimCmd, 't', cast(stimNIPTime, 'int64')));
            fprintf(logFileID, '%s, ', saveStim);
            fprintf('\nExecuting\n%s\n', saveStim);
            %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            % Train Interval
            pause(TI)
        end
        % toc;
    end
    toc;
end
fclose(logFileID);
% toc;
%%