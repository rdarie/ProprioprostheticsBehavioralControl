function [stimCmd, stimElectrodes] = high_res_stim_command_builder_stimSeq(...
    cathode_list, anode_list, Chans_paddle_to_ripple, randomizedParamList, stimStep, frequencyMultiplier)

% This function is randomizing combinations of stim parameters for a given
% combination of anode(s) and cathode(s), it returns a stimString that is
% further used to trigger the defined stimulation


% Anode = anodic pulse first (current > 0)
% Cathode = cathodic pulse first (current < 0)

% Random param list = [Freq , Amp, TL, PD, PR]

% pulse frequency
reqFreq  = randomizedParamList(1);
% pulse amplitude (first phase)
reqAmp = randomizedParamList(2);
% train length
reqTL = randomizedParamList(3);
% phase duration (first phase)
reqPD = randomizedParamList(4);
% phase ratio (second phase compared to first phase)
reqPR = randomizedParamList(5);
%% Stimulation Parameters [STIMSEQ VERSION]

% Stimulation parameters
% sprintf('Electrodes selected as cathodes are : %d  \n', cathode_list)
% sprintf('Electrodes selected as anodes are : %d  \n', anode_list)
cathode_ripple_idx = Chans_paddle_to_ripple(cathode_list);
anode_ripple_idx = Chans_paddle_to_ripple(anode_list);
cathode_list_ripple = reshape(cat(1, cathode_ripple_idx{:}), 1, []);
anode_list_ripple = reshape(cat(1, anode_ripple_idx{:}), 1, []);
% stimElectrodes must be the electrode number in terms of ripple system
% (i.e 5 on the paddle means 2 on the ripple -> provide 5 if you want 2)
% Chans_paddle_to_ripple(5) returns 2 which is the ripple index of the 5th paddle electrode !
 
% all the following parameters are the same as cathode & anode signal in a biphasic pulse are just opposites

% If current is > 1.5 mA, double the length of every vector of parameters
% as every channel will be doubled with 2nd C-bank

% Amplitude
% number of cathodes
nC             = length(cathode_list_ripple);
% number of anodes
nA             = length(anode_list_ripple);
nTotalContacts = (nC + nA);
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% divide the requested amplitude evenly among the channels
if isempty(cathode_list_ripple) && isempty(anode_list_ripple)
    error('no stim requested')
elseif isempty(cathode_list_ripple)
    stimElectrodes       = anode_list_ripple;
    phaseAmplitude_steps = ones(1, nA) * floor(reqAmp / (stimStep * nA));
    polarity  = ones(1, nA);
elseif isempty(anode_list_ripple)
    stimElectrodes       = cathode_list_ripple;
    phaseAmplitude_steps = ones(1, nC) * floor(reqAmp / (stimStep * nC));
    polarity  = zeros(1, nC);
else
    stimElectrodes       = [cathode_list_ripple, anode_list_ripple];
    phaseAmplitude_steps = [...
        ones(1, nC) * floor(reqAmp / (stimStep * nC)),...
        ones(1, nA) * floor(reqAmp / (stimStep * nA))];
    % Current flows from 1st electrode to 2nd
    polarity  = [zeros(1, nC), ones(1, nA)];
end
% duplicate the shared parameters, one for each channel
frequency_Hz         = ones(1, nTotalContacts) * reqFreq;
trainLength_ms       = ones(1, nTotalContacts) * reqTL;
phaseDuration_ms     = ones(1, nTotalContacts) * reqPD;
phaseRatios          = ones(1, nTotalContacts) * reqPR;
electrodeDelay_ms    = zeros(1, nTotalContacts);
% Generate stimulation string
if max(phaseAmplitude_steps) * stimStep > 1500
    error('Request exceeds max current!')
end

for k=1:length(stimElectrodes)
    cmd(k).elec     = stimElectrodes(k);
    periodInClockCycles = cast(floor(30e3 / frequency_Hz(k)), 'int64');
    phaseLength = round(30e3 * (phaseDuration_ms(k) / 1000));
    interWaveformPeriod = floor(periodInClockCycles / frequencyMultiplier) - (phaseLength * phaseRatios(k) + 1);
    cmd(k).period   = periodInClockCycles;
    cmd(k).repeats  = cast(ceil(trainLength_ms(k) * frequency_Hz(k) / 1000), 'int64');
    cmd(k).action   = 'allcyc';
    
    % Create the first phase (cathodic) for stimulation.  This has a 
    % duration of 200 us (6 clock cycles at 30 kHz), an amplitude of 
    % 10, and negative polarity.
    secondPhaseAmplitude = floor(phaseAmplitude_steps(k) / phaseRatios(k));
    firstPhaseAmplitude = phaseRatios(k) * secondPhaseAmplitude;
    if polarity(k)
        invPolarity = 0;
    else
        invPolarity = 1;
    end
    for extraIdx = 1:frequencyMultiplier
        cmd(k).seq((extraIdx - 1) * 3 + 1) = struct(...
            'length', phaseLength, 'ampl', firstPhaseAmplitude,...
            'pol', polarity(k), ...
            'fs', 0, 'enable', 1, 'delay', 0, 'ampSelect', 1);
        
%         % Create the inter-phase interval.  This has a duration of 100 us
%         % (3 clock cycles at 30 kHz).  The amplitude is zero.  The
%         % stimulation amp is still used so that the stim markers send by
%         % the NIP will properly contain this phase.
%         cmd(k).seq((extraIdx - 1) * 4 + 2) = struct(...
%             'length', 1, 'ampl', 0,...
%             'pol', 0, 'fs', 0, ...
%             'enable', 0, 'delay', 0, 'ampSelect', 1);
        
        % Create the second, anodic phase.  This has a duration of 200 us
        % (6 cycles at 30 kHz), and amplitude of 10, and positive polarity.
        cmd(k).seq((extraIdx - 1) * 3 + 2) = struct(...
            'length', phaseRatios(k) * phaseLength, 'ampl', secondPhaseAmplitude,...
            'pol', invPolarity, ...
            'fs', 0, 'enable', 1, 'delay', 0, 'ampSelect', 1);
        % Create the inter-biphasic waveform interval.  
        % The amplitude is zero.  The
        % stimulation amp is still used so that the stim markers send by
        % the NIP will properly contain this phase.
        cmd(k).seq((extraIdx - 1) * 3 + 3) = struct(...
            'length', 1, 'ampl', 0,...
            'pol', 0, 'fs', 0, ...
            'enable', 0, 'delay', 0, 'ampSelect', 1);
    end
end
stimCmd = cmd;
