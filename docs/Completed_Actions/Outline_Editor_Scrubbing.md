The point of this feature is to update the functionality of the Outline Editor Panel. Currently, both the editor and the reading view can make new division lines, but only the reading view can change where these divisions lie. 

The game plan is for the position of divisions to be easily changeable in the outline editor as well.

Currently references in the outline are structured like this: 
- Genesis 3:8-15
- 3:8-15
- v8-15

If you just look at the numbers before and after the hyphen, these represent a location of a division.

$\#_a - \#_b$-

- $\#_a$ has a division right above it
- $\#_b$ has a division right below it

The user should be able to hover each of these numbers and then click-and-drag to move where a division lies very similar to the user input in the reading scene.

Here is an example:

Outline - Genesis 1:1-15
1. v1-7
2. v8-15
   - v8-10
   - b. v11-15

If the user were to hover over the "7" in point 1, and drag DOWN, then the outline would trend in this direction:

Outline - Genesis 1:1-15
1. v1-9
2. v10-15
   - v10-10
   - b. v11-15


This second example shows three behaviors
1. The outline should also account for the shrinking of sub-bullets when another section is expanded.
2. The user should never be able to 'expand' a section to the point that it collapses a sub-point below 1 verse. This would be the extent that the user could drag that 1st point down because bullet 2.1 is already one verse 
3. When a point is only one verse, show the same verse on both sides of a hyphen so that the user still has two handles to move the division above the point and the division below a point.

Obviously, these same principles should work for expanding a point by dragging a section handle up, or shrinking a section by taking either handle in the opposite direction from what has already been stated. And as always, the user should never be able to collapse a section to the point that it collapses a sub-point below 1 verse. 

Outer boundaries can also be expanded to expand the entire outline.