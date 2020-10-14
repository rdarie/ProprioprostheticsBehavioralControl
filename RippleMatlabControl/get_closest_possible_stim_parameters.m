clear; clc; close all;
jsonData = jsondecode(fileread('emg_parameters2.json'));
stimResLookup = [1, 2, 5, 10, 20];

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
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
    % ignore double channel
    Chans_paddle_to_ripple = {1, 3, 5, 7, 2, 4, 6, 8,    9, 11, 13, 15, 10, 12, 14, 16,    17, 19, 21, 23, 18, 20, 22, 24};
    % split current equally
    % Chans_paddle_to_ripple = {1, 3, 5, 7, 2, 4, 6, 8,    9, 11, 13, 15, 10, 12, 14, 16,    [17; 25], [19; 27], [21; 29], [23; 31], [18; 26], [20; 28], [22; 30], [24; 32]};
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


parameter_list = [];
for j = 1:size(jsonData,1)
    disp(j)
    for i = 1:5
        disp(i)
        columnName = sprintf('proposed_EES_%d', i);
        stringsToSearch = jsonData(j).(columnName);
        [expr,res] = regexp(stringsToSearch, ' Hz, ', 'match', 'split');
        freq = str2double(res{1});
        if freq<3
            freq=3;
        end
        amp = str2double(res{2}(1: end-3));
        multiplier = jsonData(j).('ampl_multiplier');
        whichNano = jsonData(j).('whichNano');
        parameter_list = [freq, -1 * multiplier * amp, 300, .150, 3];
        
        thisPaddleToRippleLookup = Chans_paddle_to_ripple;
        for k=1:size(thisPaddleToRippleLookup, 2)
            thisPaddleToRippleLookup{i} = thisPaddleToRippleLookup{k} + (whichNano-1) * 32;
        end
        try
        [stimCmd, stimElectrodes, achievedParams] = stim_elec_combination_stimSeq(...
            jsonData(j).('cathode_list'), jsonData(j).('anode_list'), thisPaddleToRippleLookup,...
            parameter_list, stimResLookup(jsonData(j).('stimRes')));
        disp(achievedParams);
        jsonData(j).(sprintf('achieved_amplitude_%d', i)) = achievedParams(2);
        jsonData(j).(sprintf('achieved_frequency_%d', i))  = achievedParams(1);
        catch ME
            disp(ME.message);
        end
    end
end
fileID = fopen('emg_parameters2_with_achieved.json','w');
fprintf(fileID,jsonencode(jsonData));
fclose(fileID);