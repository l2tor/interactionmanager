This git includes 3 parts.
    - Some network dummy tests (/dummy)
    - The current interactionmanager (/interactionmanager)
    - A small WoZ-Gui to fake some input like VAD, Touches and Spatial Relations (/tools/TestGUIForValidatoin)

The interaction_manager stores the information about previous sessions on the harddrive of the tablet.
This system can be use for teachers in order to recover a session previously interrupted either by the child or a crash of the system.
The recovery can be done by selection the appropriated file from the ControlPannel.

Two types of file are stored:
		- NAME_ID_X.json: This files contain the necessary information to restart a session from a specific point of the lesson.
		  NAME is the name of the child. ID is the ID given for the child. X contains the number of the task and subtask the child was performing.
		  This file is written properly when the Interactionmanager has a clean exit, either the sessions ends normally or the exit
		  button on the ControlPanel has been pressed. In these cases the snapshot is copied to this "normal" memory.
		- snapshot.json: This file contains the necessary information to restart the interaction from the latest interaction of the child.
		  It should contain the same information as the latest NAME_ID_X.json file.
