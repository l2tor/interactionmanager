# Interactionmanager
This git includes the current version of the interactionmanager for the L2TOR Evaluation system.

**How to start**
It can be started with the included "interactionmanager.bat" or via a cmd window. There are only 2 mandatory and 1 optional parameters:

    --ip "xxx.xxx.xxx.xxx"  = The IP of the system the connection manager is running on (default 127.0.0.1).
    --port xxxx             = The port the connection manager is listening too (default 1111).
    --mode "xxxx"           = Defines the mode of the IM. The mode 'checkpoint' will allow to create new scene files for all checkpoints. (default:normal)
                              Checkpoints will be stored in DataModel\tablet_scenes\checkpoints

All datafiles containing the session information are stored in the Datamodel Repository, which needs to be stored
on the same level as the interaction manager. For example:
./
  -- /interactionmanager
    -- /dummy
    -- /interactionmanager
    -- /tools
    -- ...
  -- /DataModel
    -- /3dModels
    -- /converter
    -- ...

The interaction_manager stores the information about previous sessions on the harddrive. This system can be use for
experimenters in order to recover a session previously interrupted either by the child or a crash of the system. To resume
a session the experimenter has to choose and load the corresponding memory file in the ControlPannel and restart the
last session. It will continue at a checkpoint near the point of interruption.

Furthermore, two types of file are stored:
		- NAME_ID_X.json: This files contain the necessary information to restart a session from a specific point of the lesson.
		  NAME is the name of the child. ID is the ID given for the child. X contains the number of the task and subtask the child was performing.
		  This file is written properly when the Interactionmanager has a clean exit (either the sessions ends normally or the exit
		  button on the ControlPanel has been pressed). In these cases the snapshot is copied to this "normal" memory.
		- snapshot.json: This file contains the necessary information to restart the interaction from the latest interaction of the child.
		  It should contain the same information as the latest NAME_ID_X.json file.

These files can be used to reconstruct a memory file, when something went wrong and, e.g., the pc crashed.
