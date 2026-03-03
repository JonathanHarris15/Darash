It is time to update the outline system to be able to support division between words instead of just verses. The default should remain as is. Dragging a division in the reading view or the editor should increment by 1 verse, the change comes in when the user drags while holding ctrl. This should increment by 1 word. This should also be reflected in the editor and reading view. 

In the reader, the divisions should be visually represented as lines between words. In the editor the divisions should implimented by breaking verses into smaller chunks represented by a lower case letter after the reference. For example, if a verse is 1:1, it should be represented as 1:1a, 1:1b, 1:1c, etc.

So in the editor, you are not actually dividing per word, but rather just a sub-verse increment (1:1a, 1:1b, etc.)


When the ctrl-drag is being used in the reading scene, divisions lines are just not allowed to collapse a division below a single word as opposed to when they are doing a regular drag where they are allowed to collapse a division below a single verse. If the user drags a division that is between words without dragging, it should act as a regular drag and snap between verses.