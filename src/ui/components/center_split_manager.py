"""
CenterSplitManager — VS Code-style drag-to-split logic for center panels.

Lifecycle:
  1. A center panel becomes floating (user is dragging it).
  2. A 50 ms poll timer fires repeatedly:
       - Map QCursor.pos() into center_workspace coordinates.
       - For each stationary visible center panel, check whether the cursor
         is within SPLIT_BUFFER_PCT of its left or right edge.
       - If so, update _last_suggestion and show the SplitOverlayWidget.
  3. The panel becomes non-floating (user released the mouse):
       - A short singleShot delay lets Qt finish placing the dock.
       - If _last_suggestion was set, we rearrange via splitDockWidget and
         then call _apply_current_percentages() to equalize all widths.
"""
from PySide6.QtCore import QObject, QTimer, QRect, Qt
from PySide6.QtGui import QCursor


# Fraction of center_workspace width that counts as a "split edge zone".
SPLIT_BUFFER_PCT: float = 0.25


class CenterSplitManager(QObject):
    """
    Manages drag-to-split behaviour for center QDockWidgets.

    Parameters
    ----------
    main_window:
        The application's MainWindow instance.  Must expose:
          - center_workspace  (QMainWindow)
          - center_panels     (list[QDockWidget])
          - _clean_center_panels()
          - _apply_current_percentages()
    overlay:
        The SplitOverlayWidget that lives inside center_workspace.
    """

    def __init__(self, main_window, overlay):
        super().__init__(main_window)
        self._mw = main_window
        self._overlay = overlay

        self._dragged_dock = None          # dock currently being dragged
        self._last_suggestion = None       # (target_dock, 'left'|'right') or None

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(50)
        self._poll_timer.timeout.connect(self._poll_drag)

    # ------------------------------------------------------------------
    # Public slots — connect to dock.topLevelChanged
    # ------------------------------------------------------------------

    def on_panel_floating(self, is_floating: bool, dock=None) -> None:
        """
        Called when a center panel's floating state changes.

        Connect as:  dock.topLevelChanged.connect(
                         lambda f, d=dock: split_manager.on_panel_floating(f, d))
        """
        if dock is None:
            return

        if is_floating:
            self._dragged_dock = dock
            self._last_suggestion = None
            self._poll_timer.start()
        else:
            # Panel has landed — stop polling and apply split after Qt settles
            self._poll_timer.stop()
            self._overlay.clear()

            if self._last_suggestion is not None:
                suggestion = self._last_suggestion
                dragged = self._dragged_dock
                self._last_suggestion = None
                self._dragged_dock = None
                # Short delay so Qt finishes its own dock placement first
                QTimer.singleShot(60, lambda: self._apply_split(dragged, *suggestion))
            else:
                self._dragged_dock = None
                # Re-balance widths regardless (user may have just re-tabbed)
                QTimer.singleShot(60, self._mw._apply_current_percentages)

    # ------------------------------------------------------------------
    # Internal polling
    # ------------------------------------------------------------------

    def _poll_drag(self) -> None:
        cw = self._mw.center_workspace
        cursor_global = QCursor.pos()
        cursor_local = cw.mapFromGlobal(cursor_global)

        buffer_px = int(SPLIT_BUFFER_PCT * max(1, cw.width()))

        self._mw._clean_center_panels()
        candidates = [
            p for p in self._mw.center_panels
            if p is not self._dragged_dock
            and not p.isFloating()
            and p.isVisible()
        ]

        suggestion = None
        highlight_rect: QRect | None = None

        for panel in candidates:
            # geometry() in center_workspace coords
            r = panel.geometry()

            right_zone = QRect(r.right() - buffer_px, r.top(), buffer_px, r.height())
            left_zone  = QRect(r.left(),              r.top(), buffer_px, r.height())

            if right_zone.contains(cursor_local):
                suggestion = (panel, 'right')
                # Highlight the right half of the panel
                half_w = r.width() // 2
                highlight_rect = QRect(r.left() + half_w, r.top(), r.width() - half_w, r.height())
                break
            elif left_zone.contains(cursor_local):
                suggestion = (panel, 'left')
                # Highlight the left half of the panel
                half_w = r.width() // 2
                highlight_rect = QRect(r.left(), r.top(), half_w, r.height())
                break

        self._last_suggestion = suggestion

        if highlight_rect is not None:
            self._overlay.show_suggestion(highlight_rect)
        else:
            self._overlay.clear()

    # ------------------------------------------------------------------
    # Split application
    # ------------------------------------------------------------------

    def _apply_split(self, dragged_dock, target_dock, side: str) -> None:
        """
        Rearrange docks so that *dragged_dock* splits *target_dock* on
        the requested *side* ('left' or 'right'), then equalise widths.
        """
        cw = self._mw.center_workspace

        # Verify both docks are still alive and belong to center_workspace
        try:
            dragged_dock.parent()
            target_dock.parent()
        except RuntimeError:
            return

        if side == 'right':
            # splitDockWidget(A, B, Horizontal) → B appears to the right of A
            cw.splitDockWidget(target_dock, dragged_dock, Qt.Horizontal)

        else:  # 'left'
            # We want dragged on the LEFT of target.
            # Strategy: re-add dragged to top area, then split so that target
            # goes to the RIGHT of dragged.
            cw.addDockWidget(Qt.TopDockWidgetArea, dragged_dock)
            cw.splitDockWidget(dragged_dock, target_dock, Qt.Horizontal)

        # Re-equalise all center panel widths
        self._mw._apply_current_percentages()
