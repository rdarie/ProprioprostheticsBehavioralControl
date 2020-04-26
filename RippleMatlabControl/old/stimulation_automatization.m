%% Initializations 
% Clean the world
close all; fclose('all'); clc; clear all;
folderPath = 'C:\Users\Peep Sheep\Trellis\dataFiles\'
%%
% Initialize xippmex
status = xippmex;
if status ~= 1; error('Xippmex Did Not Initialize');  end


% Find all channels (they are both able to record & stim)-> size = 96

Chans_analog = xippmex('elec', 'analog');
Chans = xippmex('elec', 'nano');
FEs = unique(ceil(Chans/32));
FE_analog = unique(ceil(Chans_analog/32));

% Get NIP clock time right before turning streams on (30 kHz sampling)recChans
timeZero = xippmex('time');

%% Data Stream Activation
% Configure all electrode FE to have Stim data stream 
% active, all Raw streams to active, and deactivate all other streams
% Note only stim and spike streams are managed individually
tic;

% We need to stream stim + raw data for all electrodes as we will
% switch which one is stimulating, and which one is recording

% Only 'stim' and 'spike' data streams can be enabled and disabled on a per
% channel basis, all other data streams are enabled and disabled per front
% end basis when any channel is used for 'elecs' input

if ~isempty(Chans)
    %if analog plugged
    if analog == 0
        xippmex('signal',Chans, 'stim', ones(1,length(Chans)));
        xippmex('signal', FEs, 'raw', ones(1,length(FEs)));  
        %xippmex('signal', FE_analog, 'raw', ones(1,length(FE_analog))); 
        xippmex('signal', FEs, 'hi-res', ones(1,length(FEs)));
        xippmex('signal', FEs, 'lfp', zeros(1,length(FEs)));
        xippmex('signal', FEs, 'spk', zeros(1,length(FEs)));
    end
        xippmex('signal',Chans, 'stim', ones(1,length(Chans)));
        xippmex('signal', FEs, 'raw', ones(1,length(FEs)));   
        xippmex('signal', FEs, 'hi-res', ones(1,length(FEs)));
        xippmex('signal', FEs, 'lfp', zeros(1,length(FEs)));
        xippmex('signal', FEs, 'spk', zeros(1,length(FEs)));
end

toc;


%% Change Ripple indices to Paddle 24 indices

% which bank is connected to which headstage determines to what channels
% correspond each electrode, please set this here :
A = 'x';
B = 'y';
% Headstage stored to C bank can potentially be doubled
C = 'z';

% z assigned to C bank [electrodes 17-24 above 1.5mA]
if A == 'x' && B == 'y'&& C == 'z'
    Chans_paddle = [1, 2, 3, 4, 5 ,6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]; 
    Chans_paddle_to_ripple = {1, 3, 5, 7, 2, 4, 6, 8,    9, 11, 13, 15, 10, 12, 14, 16,    [17,25], [19, 27], [21, 29], [23, 31], [18, 26], [20, 28], [22,30], [24, 32]};
% y assigned to C bank [electrodes 9-16 above 1.5 mA]
elseif A == 'z' && B == 'x' && C == 'y'
    Chans_paddle = [1, 2, 3, 4, 5 ,6, 7, 8,    9, 10, 11, 12, 13, 14, 15, 16,   17, 18, 19, 20, 21, 22, 23, 24]; 
    Chans_paddle_to_ripple = [9,11,13,15,10,12,14,16,  [17,25] , [19,27] , [21, 29] , [23, 31] , [18, 26] , [20, 28] , [22, 30] , [24, 32] , 1, 3, 5, 7, 2, 4, 6, 8];
% x assigned to C bank [electrodes 1-8 above 1.5 mA]
elseif A == 'y' && B == 'z' && C == 'x'
    Chans_paddle = [1, 2, 3, 4, 5 ,6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]; 
    Chans_paddle_to_ripple = [ [17,25] , [19,27] , [21, 29] , [23, 31] , [18, 26] , [20, 28] , [22, 30] , [24, 32] ,     1, 3, 5, 7, 2, 4, 6, 8,       9, 11, 13, 15, 10, 12, 14, 16 ];
else 
    sprintf('Error in assigning headstages, please change A, B and C assignments')
    return;
end



%% Stimulation Settings 

% 1. Stimulation signal settings [variable/randomly chosen]

% frequencies_Hz = [30, 50, 100, 200, 300];
frequencies_Hz = [2, 4, 6];
% 40 corresponds to 20muA* 40 = 1000 microamps 
% phaseAmplitude_steps  = [400, 800, 1500, 2000, 3000] ./20;
phaseAmplitude_steps  = [240, 320, 540] ./20;

% 2. Stimulation signal settings [constant]
% get balanced freq and amp distribution 
% the only randomized parameter will be the order in which pre-defined
% combination of freq and amp are executed
[Freq, Amp] = meshgrid(frequencies_Hz, phaseAmplitude_steps);
c = cat(2, Freq', Amp');

trainLength_ms  = 20 * 1000;
phaseDuration_ms = 0.250;

% Number of combination array's copy
comb_copies = 1;
% Train interval (s)
TI = trainLength_ms / 1000 + 0.7;
% How many times to repeat the train
repetition = 1;
% To be sure to 

% To reach 50 repetition per combination, one way is to :
% 1. Generate a combination array (25x2)
% 2. Randomly pick a row in the array (i.e a combination)
% 3. Stimulate with 10 repeats of that combination
% 4. Discard the row
% 5. Repeat 2. 3. and 4. until the comb array is empty
% 6. Repeat all the previous steps 5 times to reach 50 repe    ats
% per combination randomly ordered in time 

% Cathode/Anode setting
whichNano = 1;
% 1 caudal 2 rostral
cathode_list = [9];
anode_list = [13];
%
thisPaddleToRippleLookup = Chans_paddle_to_ripple;
for i=1:size(thisPaddleToRippleLookup, 2)
    thisPaddleToRippleLookup{i} = thisPaddleToRippleLookup{i} + (whichNano-1) * 32;
end
% Execute Stim
% Iterates over combination array copies
clc
blockID = sprintf('Block000%d', 3);
logFileID = fopen(sprintf('%s20200318\\%s_autoStimLog.json', folderPath, blockID),'a');
fprintf(logFileID, '[');
for i=1:comb_copies
    comb_array = reshape(c, [], 2);
    comb_array_length = size(comb_array, 1);
    % tic;
    % Iterate over each combination inside the i-th combination array
    for j=1:comb_array_length
        fprintf('Combination %d / %d\n', [(i-1)*comb_array_length + j,comb_array_length*comb_copies])
        % Randomization in the comb list
        rd_idx = randperm(size(comb_array, 1), 1);
        random_param_list = comb_array(rd_idx, :);
        % Add constant parameters
        random_param_list = [random_param_list ,trainLength_ms, phaseDuration_ms];
        % Delete than comb from the list
        comb_array(rd_idx, :) = [];

        % fprintf('Random list of parameters is : Freq = %d  Hz,  Amp = %d,  TL = %d ms, PD = %d ms',random_param_list)

        % # repetition of each combination
        tic;
        for k=1:repetition
            % Function call to stimulate
            [stimString, stimElectrodes] = stim_elec_combination_stimSeq(cathode_list, anode_list, thisPaddleToRippleLookup, random_param_list);
            % Enable stimulation for cathodes and anodes selected previously
            xippmex('stim', 'enable', stimElectrodes);
            %if k ~= 1
               %
            %sprintf('over')
            %end
            % disp(stimString)
            % Stim time is roughly 0.5 ms -> negligeable
            saveStim = jsonencode(struct(...
                'stimString', stimString, 't', cast(xippmex('time'), 'int64')));
            fprintf(logFileID, '%s, ', saveStim);
            xippmex('stim', stimString);
            %
            t_next = xippmex('time')/30000;
            t_stop = t_next + TI;
            % Training Interval
            if k  ~= repetition
                while (t_next - t_stop) < TI
                    disp(t_next - t_stop)
                    t_next = xippmex('time')/30000;
                end
            end
            %
            %t_stop = xippmex('time')/30000;
        end
        toc;

    end
end
fprintf(logFileID, '{}]');
fclose(logFileID);
% toc;