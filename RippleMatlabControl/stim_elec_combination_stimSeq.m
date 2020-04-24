function [stimCmd, stimElectrodes] = stim_elec_combination_stimSeq(...
    cathode_list, anode_list, Chans_paddle_to_ripple, random_param_list)

% This function is randomizing combinations of stim parameters for a given
% combination of anode(s) and cathode(s), it returns a stimString that is
% further used to trigger the defined stimulation


% Anode = anodic pulse first (current > 0)
% Cathode = cathodic pulse first (current < 0)

% Random param list = [Freq , Amp, TL, PD, PR]


%% Stimulation Parameters [STIMSEQ VERSION]

% Stimulation parameters
% sprintf('Electrodes selected as cathodes are : %d  \n', cathode_list)
% sprintf('Electrodes selected as anodes are : %d  \n', anode_list)
cathode_list_ripple = [];
anode_list_ripple = [];
cathode_ripple_idx = [];
anode_ripple_idx = [];
% stimElectrodes must be the electrode number in terms of ripple system
% (i.e 5 on the paddle means 2 on the ripple -> provide 5 if you want 2)
% Chans_paddle_to_ripple(5) returns 2 which is the ripple index of the 5th paddle electrode !

% Find the the ripple channel(s) corresponding to the electrode (one cell per electrode)
for i=1:length(cathode_list)
    cathode_ripple_idx = [cathode_ripple_idx, Chans_paddle_to_ripple(cathode_list(i))];
end
for i=1:length(anode_list)
    anode_ripple_idx = [anode_ripple_idx, Chans_paddle_to_ripple(anode_list(i))];
end


% Iterate over each cathode/anode of cathode/anode list
for k=1:length(cathode_ripple_idx)
    % disp(random_param_list(2));
    % If the current amplitude is above max value (75 steps * 20 uA i.e above 1.5 mA)
    if random_param_list(2) > 75
       % Take the two channels if there are actually 2
       % (i.e if both anode/cathode are plugged on the double bank)
       if length(cathode_ripple_idx{:,k}) == 2 && length(anode_ripple_idx{:,k}) == 2
           % Add the two ripple channels to the cathode list
           cathode_list_ripple = [cathode_list_ripple, cathode_ripple_idx{:,k}];
           % Add the two other ripple channels to the anode list
           anode_list_ripple = [anode_list_ripple, anode_ripple_idx{:,k}];
       else 
           % if anode & cathode are not on the same (doubled) bank -> ERROR
           sprintf('Anode and cathode are not on the same bank, current above 1.5mA cannot be reached')
           return;
       end
       % Each of the 2 cathodes/anodes sends half of the required amplitude so that they do not each are above I_max 
       %if k = 1
       %phaseAmplitude_steps = [phaseAmplitude_steps, ones(1, length(cathode_list) + length(anode_list))*random_param_list(2)/2];
       %sprintf('cathode channels  %d %d',cathode_list_ripple)
       %sprintf('anode channels  %d %d',anode_list_ripple)

    % If the current amplitude is below max value (i.e below 1.5 mA included)
    else 
        % Add only the first ripple channels to the k-th cathode list
        cathode_list_ripple = [cathode_list_ripple, cathode_ripple_idx{k}(1)];
        % Add only the first ripple channels to the k-th anode list
        anode_list_ripple = [anode_list_ripple, anode_ripple_idx{k}(1)];
        % The amplitude can be reached with one ripple channel only, take the
        % first index
        %phaseAmplitude_steps = [phaseAmplitude_steps , ones(1, length(cathode_list_ripple) + length(anode_list_ripple))*random_param_list(2)];
        %sprintf('cathode channels : %d %d',cathode_list_ripple)
        %sprintf('anode channels  %d %d',anode_list_ripple)
    end
end
 
stimElectrodes   = [cathode_list_ripple , anode_list_ripple];
% all the following parameters are the same as cathode & anode signal in a biphasic pulse are just opposites

% If current is > 1.5 mA, double the length of every vector of parameters
% as every channel will be doubled with 2nd C-bank

if random_param_list(2) > 75
    % Amplitude divided by 2 to be assigned to two channels
    nContacts = (length(cathode_list) + length(anode_list))*2;
    phaseAmplitude_steps = ones(1, nContacts) * random_param_list(2)/2;
    frequency_Hz = ones(1, nContacts)*random_param_list(1);
    trainLength_ms = ones(1, nContacts)*random_param_list(3);
    phaseDuration_ms = ones(1, nContacts)*random_param_list(4);
    phaseRatios = ones(1, nContacts)*random_param_list(5);
    % 
    electrodeDelay_ms = ones(1, nContacts)*0;
    % Current flows from 1st electrode to 2nd
    polarity  = [ones(1, 2*length(cathode_list)), zeros(1, 2*length(anode_list))];
else 
    % Amplitude
    nContacts = (length(cathode_list) + length(anode_list));
    phaseAmplitude_steps = ones(1, nContacts)*random_param_list(2);
    frequency_Hz = ones(1, nContacts)*random_param_list(1);
    trainLength_ms = ones(1, nContacts)*random_param_list(3);
    phaseDuration_ms = ones(1, nContacts)*random_param_list(4);
    phaseRatios = ones(1, nContacts)*random_param_list(5);
    %
    electrodeDelay_ms = ones(1, nContacts)*0;
    % Current flows from 1st electrode to 2nd
    polarity  = [ones(1, length(cathode_list)), zeros(1, length(anode_list))];
end
% Generate stimulation string

for k=1:length(phaseAmplitude_steps)
    cmd(k).elec     = stimElectrodes(k);
    cmd(k).period   = round(30e3 / frequency_Hz(k));
    cmd(k).repeats  = round(trainLength_ms(k) * frequency_Hz(k) / 1000);
    cmd(k).action   = 'immed';
    
    % Create the first phase (cathodic) for stimulation.  This has a 
    % duration of 200 us (6 clock cycles at 30 kHz), an amplitude of 
    % 10, and negative polarity.
    secondPhaseAmplitude = round(phaseAmplitude_steps(k) / phaseRatios(k));
    firstPhaseAmplitude = phaseRatios(k) * secondPhaseAmplitude;
    phaseLength = round(30e3 * (phaseDuration_ms(k) / 1000));
    cmd(k).seq(1) = struct(...
        'length', phaseLength, 'ampl', firstPhaseAmplitude,...
        'pol', polarity(k), ...
        'fs', 0, 'enable', 1, 'delay', 0, 'ampSelect', 1);
    % Create the inter-phase interval.  This has a duration of 100 us
    % (3 clock cycles at 30 kHz).  The amplitude is zero.  The 
    % stimulation amp is still used so that the stim markers send by 
    % the NIP will properly contain this phase.
    cmd(k).seq(2) = struct(...
        'length', 1, 'ampl', 0,...
        'pol', 0, 'fs', 0, ...
        'enable', 0, 'delay', 0, 'ampSelect', 1);
    % Create the second, anodic phase.  This has a duration of 200 us 
    % (6 cycles at 30 kHz), and amplitude of 10, and positive polarity.
    if polarity(k)
        invPolarity = 0;
    else
        invPolarity = 1;
    end
    cmd(k).seq(3) = struct(...
        'length', phaseRatios(k) * phaseLength, 'ampl', secondPhaseAmplitude,...
        'pol', invPolarity, ...
        'fs', 0, 'enable', 1, 'delay', 0, 'ampSelect', 1);
end
stimCmd = cmd;
