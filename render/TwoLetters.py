from manim import *
import numpy as np
from typing import Optional, List, Tuple

# ---- Palette / style (minimalistic light theme) -----------------------------
BG_COLOR  = "#FFFFFF"     # white background
INK_1     = "#141414"     # near-black  (first name / first initial)
INK_2     = "#8A8A8A"     # soft gray   (last name  / second initial)
EPICYCLE  = "#3A8FB5"     # light blue Fourier circles (darker shade)
EPICYCLE_ALPHA = 0.92
FONT_NAME = "Great Vibes"  # cursive script (baked into Docker image; install fonts/GreatVibes-Regular.ttf locally)


class TwoLetters(MovingCameraScene):
    # ------------------- Tunables / constants ---------------------------------
    text_string     = "SP"
    n_vectors       = 51
    n_samples       = 8192
    letter_duration = 3.5

    end_fade   = True
    end_fade_start = 0.97

    live_eps   = 1e-5
    EPS        = 1e-7

    # visuals (thinned out for a minimal look)
    circle_min_r     = 0.03
    circle_alpha     = 0.45
    circle_width     = 1.0
    intro_line_w     = 1.2
    intro_build_time = 1.8

    # ------------------- Helpers ----------------------------------------------
    def get_freqs(self, count=None):
        if count is None:
            count = self.n_vectors
        order = [0]
        k = 1
        while len(order) < count:
            order.extend([k, -k])
            k += 1
        return order[:count]

    def get_coefficients_of_path(self, path: VMobject, n_samples=None, freqs=None):
        if n_samples is None:
            n_samples = self.n_samples
        if freqs is None:
            freqs = self.get_freqs()

        ts  = np.linspace(0.0, 1.0, n_samples, endpoint=False)
        pts = np.array([path.point_from_proportion(t) for t in ts])
        xy  = pts[:, :2]
        z   = xy[:, 0] + 1j * xy[:, 1]

        freqs_arr = np.array(freqs)
        K         = np.exp(-TAU * 1j * np.outer(ts, freqs_arr))
        coefs     = z @ K * (1.0 / n_samples)
        return coefs, freqs_arr

    def _char_glyphs_in_order(self, t: Text):
        return [m for m in t.submobjects if isinstance(m, VMobject) and m.get_num_points() > 0]

    def get_letter_vms(self):
        text = Text(self.text_string, weight=NORMAL, font=FONT_NAME).scale_to_fit_width(10)
        glyphs = self._char_glyphs_in_order(text)
        for g in glyphs:
            g.set_fill(opacity=0).set_stroke(opacity=0)
        return text, glyphs

    def _freeze_system_to_path(self, sys_dict):
        if "trail_layers" in sys_dict and sys_dict["trail_layers"]:
            top_layer = sys_dict["trail_layers"][0]
            frozen = top_layer.copy()
            frozen.clear_updaters()
            frozen.set_stroke(opacity=1.0, width=3.5)
        else:
            frozen = VMobject().set_stroke(width=3.5, opacity=1.0)

        sys_dict["stop"]()
        for key in ("trail_layers", "vectors", "tip_dot"):
            if key in sys_dict:
                sys_dict[key].clear_updaters()
        return frozen

    def build_system(
        self,
        glyph: VMobject,
        color,
        hub,
        u_tracker: ValueTracker,
        reverse_path: bool = False,
        amp_mult: Optional[ValueTracker] = None,
        trace_lock_to_amp: bool = True,
        trail_spec: Optional[List[Tuple[float, float, float]]] = None,
    ):
        # Fourier setup
        freqs_probe = self.get_freqs(self.n_vectors * 2)
        coefs_full, freqs_full = self.get_coefficients_of_path(glyph, self.n_samples, freqs_probe)
        idx_sorted = np.argsort(-np.abs(coefs_full))
        keep_idx   = idx_sorted[: self.n_vectors]
        coefs_keep = coefs_full[keep_idx]
        freqs_keep = freqs_full[keep_idx]

        pos = {int(k): i for i, k in enumerate(freqs_keep.tolist())}
        order = []
        if 0 in pos: order.append(0)
        k = 1
        while len(order) < len(freqs_keep):
            if k in pos: order.append(k)
            if -k in pos and len(order) < len(freqs_keep): order.append(-k)
            k += 1
        order_idx = [pos[k] for k in order]
        coefs     = coefs_keep[order_idx]
        freqs_arr = freqs_keep[order_idx]

        # Machinery (arrows + circles)
        vectors = VGroup()
        origin = np.array([0.0, 0.0, 0.0])
        for i in range(len(freqs_arr)):
            a = coefs[i]
            tip0 = np.array([a.real, a.imag, 0.0])
            arrow = Arrow(
                start=origin, end=origin + tip0, buff=0, stroke_width=1.2,
                max_tip_length_to_length_ratio=0.12
            ).set_color(color).set_z_index(100)

            r = max(float(abs(a)), self.circle_min_r)
            circ = Circle(radius=1.0).set_stroke(
                width=self.circle_width, color=EPICYCLE, opacity=EPICYCLE_ALPHA
            )
            circ.set(width=2 * r, height=2 * r)
            circ.move_to(arrow.get_start()).set_z_index(50)

            if amp_mult is not None and amp_mult.get_value() < 0.999:
                arrow.set_stroke(opacity=0.0)
                circ.set_stroke(opacity=0.0)

            vectors.add(VGroup(arrow, circ))
            origin = arrow.get_end()

        tip_dot = Dot(radius=0.03, color=color).set_z_index(200)

        # Intro helpers
        intro_lines = VGroup()
        intro_arcs  = VGroup()
        if amp_mult is not None:
            for _ in range(len(freqs_arr)):
                line = Line(ORIGIN, self.EPS * RIGHT).set_stroke(color=color, width=self.intro_line_w, opacity=1.0).set_z_index(90)
                arc  = Arc(radius=self.circle_min_r, start_angle=0, angle=0).set_stroke(
                    color=EPICYCLE, width=self.circle_width, opacity=EPICYCLE_ALPHA
                ).set_z_index(45)
                intro_lines.add(line)
                intro_arcs.add(arc)

        # Fading trail (shared history)
        history: List[Tuple[float, np.ndarray]] = []
        trail_layers = VGroup()
        spec = trail_spec or [(1.0, 1.0, 2.0), (2.0, 0.55, 1.6), (2.5, 0.25, 1.2)]
        for idx, (max_age, op, w) in enumerate(spec):
            m = VMobject().set_stroke(color=color, width=w, opacity=op).set_z_index(500)
            # NOTE: keep the head DARK (do not brighten toward white on a white bg)
            if idx == 0:
                m.set_stroke(color=color, width=max(w, 3.0), opacity=1.0)
            elif idx == 1:
                m.set_stroke(color=color, width=max(w, 2.4), opacity=max(op, 0.85))
            m.max_age = max_age
            trail_layers.add(m)

        # ---------------------- Updaters ----------------------------------------
        def vectors_updater(mobj: VGroup, dt):
            u_now   = u_tracker.get_value()
            u_phase = u_now % 1.0
            u_eff   = 1.0 - u_phase if reverse_path else u_phase

            if self.end_fade and getattr(self, "total_passes", 1) > 0:
                u_abs = min(1.0, u_now / float(self.total_passes))
                fade = 0.0 if u_abs <= self.end_fade_start else min(1.0, (u_abs - self.end_fade_start) / (1.0 - self.end_fade_start))
            else:
                fade = 0.0
            op = 1.0 - fade

            s = amp_mult.get_value() if amp_mult is not None else 1.0

            if amp_mult is not None and s < 0.999:
                for i in range(len(freqs_arr)):
                    arrow, circ = mobj[i]
                    arrow.set_stroke(opacity=0.0)
                    circ.set_stroke(opacity=0.0)

                phases = TAU * freqs_arr * u_eff
                n = len(freqs_arr); t = s

                full_xy = []
                for i in range(n):
                    a_full = coefs[i]
                    tip_c  = a_full * np.exp(1j * phases[i])
                    full_xy.append(np.array([tip_c.real, tip_c.imag, 0.0]))

                origin_loc = np.array(hub)
                for i in range(n):
                    start_i = origin_loc + (t * np.sum(full_xy[:i], axis=0) if i > 0 else 0)
                    end_i   = start_i + full_xy[i] * max(t, 0.0)

                    arc = intro_arcs[i]
                    r_now = max(float(abs(coefs[i])), self.circle_min_r)
                    new_arc = Arc(radius=r_now, start_angle=0, angle=-TAU * t)
                    new_arc.move_to(start_i)
                    arc.become(new_arc)
                    arc.set_stroke(
                        color=EPICYCLE, width=self.circle_width,
                        opacity=(0.0 if t < 1e-4 else EPICYCLE_ALPHA * op)
                    )

                    line = intro_lines[i]
                    if t <= 1e-6:
                        line.set_points_as_corners(np.array([start_i, start_i + self.EPS * RIGHT], dtype=float))
                    else:
                        line.put_start_and_end_on(start_i, end_i)
                    line.set_stroke(opacity=op, width=self.intro_line_w)

                tip_dot.set_fill(opacity=0.0).set_stroke(opacity=0.0)
                return

            phases = TAU * freqs_arr * u_eff
            origin_loc = np.array(hub)
            for i in range(len(freqs_arr)):
                a = coefs[i]
                tip_c = a * np.exp(1j * phases[i])
                end_xy = np.array([tip_c.real, tip_c.imag, 0.0])

                arrow, circ = mobj[i]
                arrow.put_start_and_end_on(origin_loc, origin_loc + end_xy)
                arrow.set_stroke(opacity=op)

                r_now = max(float(abs(a)), self.circle_min_r)
                circ.set(width=2 * r_now, height=2 * r_now)
                circ.move_to(arrow.get_start())
                circ.set_stroke(
                    color=EPICYCLE, width=self.circle_width, opacity=EPICYCLE_ALPHA * op
                )

                origin_loc = arrow.get_end()

            tip_dot.move_to(origin_loc)
            tip_dot.set_fill(opacity=op).set_stroke(opacity=op)

            now = self.renderer.time
            if not history or np.linalg.norm(origin_loc - history[-1][1]) > self.live_eps:
                history.append((now, origin_loc.copy()))
                if history:
                    max_keep = max([layer.max_age for layer in trail_layers]) if len(trail_layers) > 0 else 0.0
                    cutoff = now - (max_keep + 0.5)
                    i = 0
                    while i < len(history) and history[i][0] < cutoff:
                        i += 1
                    if i > 0:
                        del history[:i]

        vectors.add_updater(vectors_updater)

        def make_trail_updater(max_age_layer):
            def _u(m: VMobject, dt):
                if trace_lock_to_amp and amp_mult is not None and amp_mult.get_value() < 0.999:
                    return
                if not history:
                    return
                now = self.renderer.time
                recent = [p for (t, p) in history if now - t <= max_age_layer]
                if len(recent) < 2:
                    p0 = history[-1][1]
                    m.set_points_as_corners(np.array([p0, p0 + self.EPS * RIGHT], dtype=float))
                    return
                pts = [recent[0]]
                for p in recent[1:]:
                    if np.linalg.norm(p - pts[-1]) > self.live_eps:
                        pts.append(p)
                if len(pts) < 2:
                    pts.append(pts[0] + self.EPS * RIGHT)
                m.set_points_as_corners(np.array(pts, dtype=float))
            return _u

        for layer, (max_age, op, w) in zip(trail_layers, spec):
            layer.add_updater(make_trail_updater(max_age))

        def stop():
            vectors.remove_updater(vectors_updater)
            for m in trail_layers:
                m.clear_updaters()
            tip_dot.clear_updaters()
            if len(intro_lines) > 0: intro_lines.clear_updaters()
            if len(intro_arcs)  > 0: intro_arcs.clear_updaters()

        sys = {
            "vectors": vectors,
            "tip_dot": tip_dot,
            "trail_layers": trail_layers,
            "history": history,
            "stop": stop,
            "color": color,
        }
        if amp_mult is not None:
            sys["intro_lines"] = intro_lines
            sys["intro_arcs"]  = intro_arcs
        return sys

    # ------------------- Scene -------------------------------------------------
    def construct(self):
        self.camera.background_color = BG_COLOR  # white background

        text, glyphs = self.get_letter_vms()
        glyphs = sorted(glyphs, key=lambda g: g.get_center()[0])
        glyph_E, glyph_L = glyphs[0], glyphs[1]

        frame = self.camera.frame
        frame.save_state()
        frame.move_to(text.get_center())
        frame.set(height=text.height * 1.6)

        text.set_opacity(0)
        self.add(text)

        hub_shared = 0.5 * (glyph_E.get_center() + glyph_L.get_center())

        draw_multiplier = 1.8
        forward_time    = self.letter_duration * draw_multiplier
        cycles          = 3
        self.total_passes = cycles
        self.end_fade_start = (cycles - 1) / cycles

        head_age = 0.18 * forward_time
        halo_age = 0.30 * forward_time
        core_age = 0.48 * forward_time
        far_age  = 0.65 * forward_time
        trail_spec = [
            (head_age, 1.00, 3.0),
            (halo_age, 0.85, 2.4),
            (core_age, 0.55, 1.8),
            (far_age,  0.25, 1.4),
        ]

        intro_amp = ValueTracker(0.0)
        self.u = ValueTracker(0.0)

        sys_E = self.build_system(glyph_E, INK_1, hub_shared, self.u,
                                  reverse_path=False, amp_mult=intro_amp, trace_lock_to_amp=True,
                                  trail_spec=trail_spec)
        sys_L = self.build_system(glyph_L, INK_2, hub_shared, self.u,
                                  reverse_path=True,  amp_mult=intro_amp, trace_lock_to_amp=True,
                                  trail_spec=trail_spec)

        solid_E = glyph_E.copy().set_fill(INK_1, 1.0).set_stroke(width=0, opacity=0).set_opacity(0.0).set_z_index(900)
        solid_L = glyph_L.copy().set_fill(INK_2, 1.0).set_stroke(width=0, opacity=0).set_opacity(0.0).set_z_index(900)
        self.add(solid_E, solid_L)
        self.solid_E = solid_E
        self.solid_L = solid_L

        if "intro_lines" in sys_E: self.add(sys_E["intro_lines"])
        if "intro_arcs"  in sys_E: self.add(sys_E["intro_arcs"])
        if "intro_lines" in sys_L: self.add(sys_L["intro_lines"])
        if "intro_arcs"  in sys_L: self.add(sys_L["intro_arcs"])

        self.add(sys_E["vectors"], sys_L["vectors"], sys_E["tip_dot"], sys_L["tip_dot"])
        self.add(*sys_E["trail_layers"], *sys_L["trail_layers"])

        self.play(intro_amp.animate.set_value(1.0), run_time=self.intro_build_time, rate_func=smooth)

        if "intro_lines" in sys_E: self.play(FadeOut(sys_E["intro_lines"], run_time=0.2))
        if "intro_arcs"  in sys_E: self.play(FadeOut(sys_E["intro_arcs"],  run_time=0.2))
        if "intro_lines" in sys_L: self.play(FadeOut(sys_L["intro_lines"], run_time=0.2))
        if "intro_arcs"  in sys_L: self.play(FadeOut(sys_L["intro_arcs"],  run_time=0.2))

        total_draw_time    = cycles * forward_time
        time_before_last   = (cycles - 1) * forward_time
        zoom_start_offset  = 5.0

        partA = min(zoom_start_offset, time_before_last)
        if partA > 0:
            self.play(
                self.u.animate.set_value(self.u.get_value() + partA / forward_time),
                run_time=partA, rate_func=linear
            )

        partB = time_before_last - partA
        if partB > 0:
            target_height_mid = frame.get_height() * 1.12
            self.play(
                AnimationGroup(
                    self.u.animate.set_value(self.u.get_value() + partB / forward_time),
                    frame.animate.set(height=target_height_mid),
                    lag_ratio=0.0
                ),
                run_time=partB, rate_func=linear
            )

        last_cycle_zoom_target = frame.get_height() * 1.20
        self.play(
            AnimationGroup(
                self.u.animate.set_value(self.u.get_value() + 1.0),
                frame.animate.set(height=last_cycle_zoom_target),
                solid_E.animate.set_opacity(1.0),
                solid_L.animate.set_opacity(1.0),
                lag_ratio=0.0
            ),
            run_time=forward_time, rate_func=linear
        )

        self.play(
            AnimationGroup(
                self.solid_E.animate.scale(1.04, about_point=self.solid_E.get_center()),
                self.solid_L.animate.scale(1.04, about_point=self.solid_L.get_center()),
                lag_ratio=0.0
            ),
            run_time=0.18, rate_func=there_and_back
        )

        self.play(
            FadeOut(sys_E["vectors"], run_time=0.4),
            FadeOut(sys_L["vectors"], run_time=0.4),
            FadeOut(sys_E["tip_dot"], run_time=0.4),
            FadeOut(sys_L["tip_dot"], run_time=0.4),
            *[FadeOut(m, run_time=0.4) for m in sys_E["trail_layers"]],
            *[FadeOut(m, run_time=0.4) for m in sys_L["trail_layers"]],
        )

        self.wait(0.3)


# -----------------------------------------------------------------------------
# Two-letter intro → full name reveal (SP → SHIVEN / PATEL)
# Uncomment this class and comment out FullName_FFTReveal to restore.
# -----------------------------------------------------------------------------
# class ELToFullName_FFTReveal(TwoLetters):
#
#     def construct(self):
#         super().construct()
#
#         frame = self.camera.frame
#         C  = frame.get_center()
#         H0 = frame.get_height(); W0 = frame.get_width()
#
#         zoom_factor = 1.35
#         H1 = H0 * zoom_factor
#         W1 = W0 * zoom_factor
#
#         solid_S = self.solid_E
#         solid_P = self.solid_L
#
#         shiven_model = Text("SHIVEN", weight=NORMAL, font=FONT_NAME).set_fill(INK_1, 1.0).set_stroke(width=0)
#         pat_model    = Text("PATEL",  weight=NORMAL, font=FONT_NAME).set_fill(INK_2, 1.0).set_stroke(width=0)
#
#         pat_model.scale_to_fit_width(0.76 * W1).move_to(C)
#         shiven_model.set(width=0.90 * pat_model.width)
#         line_gap = 0.16 * H1
#         shiven_model.next_to(pat_model, UP, buff=line_gap)
#         VGroup(shiven_model, pat_model).move_to(C)
#
#         for g in self._char_glyphs_in_order(shiven_model):
#             g.set_fill(opacity=0).set_stroke(opacity=0)
#         for g in self._char_glyphs_in_order(pat_model):
#             g.set_fill(opacity=0).set_stroke(opacity=0)
#
#         sh_gs  = self._char_glyphs_in_order(shiven_model)
#         pat_gs = self._char_glyphs_in_order(pat_model)
#
#         s_final = sh_gs[0].copy().set_fill(INK_1, 1.0).set_stroke(width=0, opacity=0)
#         p_final = pat_gs[0].copy().set_fill(INK_2, 1.0).set_stroke(width=0, opacity=0)
#
#         solid_S.generate_target()
#         solid_S.target.become(s_final)
#         solid_P.generate_target()
#         solid_P.target.become(p_final)
#
#         self.add(shiven_model, pat_model)
#
#         def glyphs_of(t: Text):
#             gs = self._char_glyphs_in_order(t)
#             for g in gs:
#                 g.set_fill(opacity=0).set_stroke(opacity=0)
#             return gs
#
#         shiven_glyphs = glyphs_of(shiven_model)[1:]
#         pat_glyphs    = glyphs_of(pat_model)[1:]
#
#         draw_multiplier = 1.8
#         forward_time    = self.letter_duration * draw_multiplier
#         cycles_fft      = 1
#         self.total_passes = cycles_fft
#
#         fade_start_abs = 0.78
#         self.end_fade_start = fade_start_abs
#
#         head_age = 0.18 * forward_time
#         halo_age = 0.30 * forward_time
#         core_age = 0.48 * forward_time
#         far_age  = 0.65 * forward_time
#         trail_spec = [
#             (head_age, 1.00, 3.0),
#             (halo_age, 0.85, 2.4),
#             (core_age, 0.55, 1.8),
#             (far_age,  0.25, 1.4),
#         ]
#
#         intro_top = ValueTracker(0.0)
#         intro_bot = ValueTracker(0.0)
#         u_fft     = ValueTracker(0.0)
#
#         systems_top, systems_bot = [], []
#         for g in shiven_glyphs:
#             systems_top.append(
#                 self.build_system(g, INK_1, ORIGIN, u_fft,
#                                   reverse_path=False, amp_mult=intro_top,
#                                   trace_lock_to_amp=True, trail_spec=trail_spec)
#             )
#         for g in pat_glyphs:
#             systems_bot.append(
#                 self.build_system(g, INK_2, ORIGIN, u_fft,
#                                   reverse_path=False, amp_mult=intro_bot,
#                                   trace_lock_to_amp=True, trail_spec=trail_spec)
#             )
#
#         for sys in systems_top + systems_bot:
#             if "intro_lines" in sys: self.add(sys["intro_lines"])
#             if "intro_arcs"  in sys: self.add(sys["intro_arcs"])
#         for sys in systems_top + systems_bot:
#             self.add(sys["vectors"], sys["tip_dot"])
#         for sys in systems_top + systems_bot:
#             self.add(*sys["trail_layers"])
#
#         self.play(
#             AnimationGroup(
#                 frame.animate.set(height=H1),
#                 MoveToTarget(solid_S),
#                 MoveToTarget(solid_P),
#                 intro_top.animate.set_value(1.0),
#                 intro_bot.animate.set_value(1.0),
#                 lag_ratio=0.0
#             ),
#             run_time=self.intro_build_time, rate_func=smooth
#         )
#
#         fades = []
#         for sys in systems_top + systems_bot:
#             if "intro_lines" in sys: fades.append(FadeOut(sys["intro_lines"], run_time=0.2))
#             if "intro_arcs"  in sys: fades.append(FadeOut(sys["intro_arcs"],  run_time=0.2))
#         if fades:
#             self.play(*fades)
#
#         solid_shiven = Text("SHIVEN", weight=NORMAL, font=FONT_NAME).set_fill(INK_1, 1.0).set_stroke(width=0)
#         solid_shiven.set_width(shiven_model.width).move_to(shiven_model).set_opacity(0.0).set_z_index(960)
#         solid_pat = Text("PATEL", weight=NORMAL, font=FONT_NAME).set_fill(INK_2, 1.0).set_stroke(width=0)
#         solid_pat.set_width(pat_model.width).move_to(pat_model).set_opacity(0.0).set_z_index(960)
#         self.add(solid_shiven, solid_pat)
#
#         t1 = fade_start_abs * forward_time
#         if t1 > 0:
#             self.play(u_fft.animate.set_value(fade_start_abs), run_time=t1, rate_func=linear)
#
#         t2 = (1.0 - fade_start_abs) * forward_time
#         self.play(
#             AnimationGroup(
#                 u_fft.animate.set_value(1.0),
#                 solid_shiven.animate.set_opacity(1.0),
#                 solid_pat.animate.set_opacity(1.0),
#                 solid_S.animate.set_opacity(0.0),
#                 solid_P.animate.set_opacity(0.0),
#                 lag_ratio=0.0
#             ),
#             run_time=t2, rate_func=linear
#         )
#
#         def freeze_outline(sys, color, width=2.6, op=0.85):
#             layer = sys["trail_layers"][0].copy()
#             layer.clear_updaters()
#             layer.set_stroke(color=color, width=width, opacity=op).set_z_index(940)
#             return layer
#
#         outline_top = VGroup(*[freeze_outline(sys, INK_1) for sys in systems_top])
#         outline_bot = VGroup(*[freeze_outline(sys, INK_2) for sys in systems_bot])
#         self.add(outline_top, outline_bot)
#
#         self.play(
#             AnimationGroup(
#                 outline_top.animate.set_stroke(width=4.0, opacity=1.0),
#                 outline_bot.animate.set_stroke(width=4.0, opacity=1.0),
#                 lag_ratio=0.0
#             ),
#             run_time=0.24, rate_func=there_and_back
#         )
#
#         machine_fades = []
#         for sys in systems_top + systems_bot:
#             machine_fades.extend([
#                 FadeOut(sys["vectors"], run_time=0.6),
#                 FadeOut(sys["tip_dot"], run_time=0.6),
#                 *[FadeOut(m, run_time=0.6) for m in sys["trail_layers"]],
#             ])
#         if machine_fades:
#             self.play(AnimationGroup(*machine_fades, lag_ratio=0.0), run_time=0.6, rate_func=smooth)
#
#         self.play(
#             AnimationGroup(
#                 outline_top.animate.set_stroke(opacity=0.0, width=3.4),
#                 outline_bot.animate.set_stroke(opacity=0.0, width=3.4),
#                 lag_ratio=0.0
#             ),
#             run_time=0.35, rate_func=smooth
#         )
#
#         final_lockup = VGroup(solid_shiven, solid_pat).move_to(C)
#         self.play(final_lockup.animate.shift(0.02 * UP), run_time=0.25, rate_func=there_and_back)
#         self.wait(0.7)


class FullName_FFTReveal(TwoLetters):
    """Draw SHIVEN / PATEL directly — no SP intro phase."""

    def construct(self):
        self.camera.background_color = BG_COLOR

        frame = self.camera.frame
        C = ORIGIN
        W0 = frame.get_width()
        H0 = frame.get_height()

        shiven_model = Text("SHIVEN", weight=NORMAL, font=FONT_NAME).set_fill(INK_1, 1.0).set_stroke(width=0)
        pat_model    = Text("PATEL",  weight=NORMAL, font=FONT_NAME).set_fill(INK_2, 1.0).set_stroke(width=0)

        pat_model.scale_to_fit_width(0.76 * W0).move_to(C)
        shiven_model.set(width=0.90 * pat_model.width)
        line_gap = 0.16 * H0
        shiven_model.next_to(pat_model, UP, buff=line_gap)
        lockup = VGroup(shiven_model, pat_model).move_to(C)

        frame.move_to(lockup.get_center())
        frame.set(height=lockup.height * 1.8)

        def glyphs_of(t: Text):
            gs = self._char_glyphs_in_order(t)
            for g in gs:
                g.set_fill(opacity=0).set_stroke(opacity=0)
            return gs

        shiven_glyphs = glyphs_of(shiven_model)
        pat_glyphs    = glyphs_of(pat_model)
        self.add(shiven_model, pat_model)

        draw_multiplier = 1.8
        forward_time    = self.letter_duration * draw_multiplier
        cycles_fft      = 1
        self.total_passes = cycles_fft

        fade_start_abs = 0.78
        self.end_fade_start = fade_start_abs

        head_age = 0.18 * forward_time
        halo_age = 0.30 * forward_time
        core_age = 0.48 * forward_time
        far_age  = 0.65 * forward_time
        trail_spec = [
            (head_age, 1.00, 3.0),
            (halo_age, 0.85, 2.4),
            (core_age, 0.55, 1.8),
            (far_age,  0.25, 1.4),
        ]

        intro_top = ValueTracker(0.0)
        intro_bot = ValueTracker(0.0)
        u_fft     = ValueTracker(0.0)

        systems_top, systems_bot = [], []
        for g in shiven_glyphs:
            systems_top.append(
                self.build_system(g, INK_1, ORIGIN, u_fft,
                                  reverse_path=False, amp_mult=intro_top,
                                  trace_lock_to_amp=True, trail_spec=trail_spec)
            )
        for g in pat_glyphs:
            systems_bot.append(
                self.build_system(g, INK_2, ORIGIN, u_fft,
                                  reverse_path=False, amp_mult=intro_bot,
                                  trace_lock_to_amp=True, trail_spec=trail_spec)
            )

        for sys in systems_top + systems_bot:
            if "intro_lines" in sys:
                self.add(sys["intro_lines"])
            if "intro_arcs" in sys:
                self.add(sys["intro_arcs"])
        for sys in systems_top + systems_bot:
            self.add(sys["vectors"], sys["tip_dot"])
        for sys in systems_top + systems_bot:
            self.add(*sys["trail_layers"])

        self.play(
            AnimationGroup(
                intro_top.animate.set_value(1.0),
                intro_bot.animate.set_value(1.0),
                lag_ratio=0.0
            ),
            run_time=self.intro_build_time,
            rate_func=smooth
        )

        fades = []
        for sys in systems_top + systems_bot:
            if "intro_lines" in sys:
                fades.append(FadeOut(sys["intro_lines"], run_time=0.2))
            if "intro_arcs" in sys:
                fades.append(FadeOut(sys["intro_arcs"], run_time=0.2))
        if fades:
            self.play(*fades)

        solid_shiven = Text("SHIVEN", weight=NORMAL, font=FONT_NAME).set_fill(INK_1, 1.0).set_stroke(width=0)
        solid_shiven.set_width(shiven_model.width).move_to(shiven_model).set_opacity(0.0).set_z_index(960)
        solid_pat = Text("PATEL", weight=NORMAL, font=FONT_NAME).set_fill(INK_2, 1.0).set_stroke(width=0)
        solid_pat.set_width(pat_model.width).move_to(pat_model).set_opacity(0.0).set_z_index(960)
        self.add(solid_shiven, solid_pat)

        t1 = fade_start_abs * forward_time
        if t1 > 0:
            self.play(u_fft.animate.set_value(fade_start_abs), run_time=t1, rate_func=linear)

        t2 = (1.0 - fade_start_abs) * forward_time
        self.play(
            AnimationGroup(
                u_fft.animate.set_value(1.0),
                solid_shiven.animate.set_opacity(1.0),
                solid_pat.animate.set_opacity(1.0),
                lag_ratio=0.0
            ),
            run_time=t2,
            rate_func=linear
        )

        def freeze_outline(sys, color, width=2.6, op=0.85):
            layer = sys["trail_layers"][0].copy()
            layer.clear_updaters()
            layer.set_stroke(color=color, width=width, opacity=op).set_z_index(940)
            return layer

        outline_top = VGroup(*[freeze_outline(sys, INK_1) for sys in systems_top])
        outline_bot = VGroup(*[freeze_outline(sys, INK_2) for sys in systems_bot])
        self.add(outline_top, outline_bot)

        self.play(
            AnimationGroup(
                outline_top.animate.set_stroke(width=4.0, opacity=1.0),
                outline_bot.animate.set_stroke(width=4.0, opacity=1.0),
                lag_ratio=0.0
            ),
            run_time=0.24,
            rate_func=there_and_back
        )

        machine_fades = []
        for sys in systems_top + systems_bot:
            machine_fades.extend([
                FadeOut(sys["vectors"], run_time=0.6),
                FadeOut(sys["tip_dot"], run_time=0.6),
                *[FadeOut(m, run_time=0.6) for m in sys["trail_layers"]],
            ])
        if machine_fades:
            self.play(AnimationGroup(*machine_fades, lag_ratio=0.0), run_time=0.6, rate_func=smooth)

        self.play(
            AnimationGroup(
                outline_top.animate.set_stroke(opacity=0.0, width=3.4),
                outline_bot.animate.set_stroke(opacity=0.0, width=3.4),
                lag_ratio=0.0
            ),
            run_time=0.35,
            rate_func=smooth
        )

        final_lockup = VGroup(solid_shiven, solid_pat).move_to(C)
        self.play(final_lockup.animate.shift(0.02 * UP), run_time=0.25, rate_func=there_and_back)
        self.wait(0.7)
