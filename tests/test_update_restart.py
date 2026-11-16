from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from auto_update import RestartCountdown, restart_installed, live_update_blockers


class UpdateRestartTests(unittest.TestCase):
    def test_countdown_restarts_after_three_ticks_not_before(self):
        window, display, restart = Mock(), Mock(), Mock()
        countdown = RestartCountdown(window, display, restart)
        countdown.start()
        display.assert_called_with(3)
        for value in (2, 1):
            countdown.tick()
            display.assert_called_with(value)
            restart.assert_not_called()
        countdown.tick()
        restart.assert_called_once()
        countdown.tick()
        restart.assert_called_once()

    def test_later_cancels_timer_and_prevents_restart(self):
        window, restart = Mock(), Mock()
        countdown = RestartCountdown(window, Mock(), restart)
        countdown.start()
        countdown.cancel()
        window.after_cancel.assert_called_once()
        for _ in range(4):
            countdown.tick()
        restart.assert_not_called()

    def app(self):
        return SimpleNamespace(plugins={}, winfo_children=lambda: [], _pipeline_busy=0,
                               _save_all_settings=Mock(), quit_app=Mock())

    def test_restart_installed_saves_then_uses_wait_helper_without_redownload(self):
        app = self.app()
        with patch('release_scheduler.spawn') as spawn, patch('release_scheduler.python_executable', return_value='pythonw'):
            restart_installed(app, Path('/app'))
        app._save_all_settings.assert_called_once()
        spawn.assert_called_once_with(['pythonw', '/app/release_scheduler.py', '--restart', '/app', '-', '-'])
        app.quit_app.assert_called_once()

    def test_unsaved_work_blocks_restart(self):
        app = self.app()
        app.plugins['gallery'] = SimpleNamespace(sort_changed=True)
        with patch('release_scheduler.spawn') as spawn:
            with self.assertRaisesRegex(RuntimeError, 'uppskjuten'):
                restart_installed(app, '/app')
        spawn.assert_not_called()
        app.quit_app.assert_not_called()

    def test_pipeline_blocks_install_and_restart(self):
        app = self.app()
        app._pipeline_busy = 1
        self.assertIn('pipeline körs', live_update_blockers(app))
        with self.assertRaises(RuntimeError):
            restart_installed(app, '/app')
        app.quit_app.assert_not_called()

    def test_save_failure_does_not_launch_or_quit(self):
        app = self.app()
        app._save_all_settings.side_effect = OSError('disk full')
        with patch('release_scheduler.spawn') as spawn, self.assertRaises(OSError):
            restart_installed(app, '/app')
        spawn.assert_not_called()
        app.quit_app.assert_not_called()

    def test_manual_check_installs_immediately_then_offers_restart_even_in_off_mode(self):
        import auto_update
        import sys
        from unittest.mock import MagicMock
        callbacks = []
        root = MagicMock()
        root.after.side_effect = lambda delay, callback: callbacks.append(callback)
        app = self.app()
        fake_tk = SimpleNamespace(Toplevel=Mock(return_value=root), Label=MagicMock(), messagebox=MagicMock())
        def thread(*args, **kwargs):
            return SimpleNamespace(start=lambda: kwargs['target'](*kwargs.get('args', ())))
        release = ('v1.0.0', 'a' * 40)
        with patch.dict(sys.modules, {'tkinter': fake_tk, 'tkinter.messagebox': MagicMock()}), \
                patch('app_icon.apply_tk_window_icon'), \
                patch('auto_update.update_settings', return_value={'mode': 'off'}), \
                patch('auto_update.save_update_settings'), \
                patch('auto_update.check_release', return_value=release), \
                patch('auto_update.apply_release', return_value='Installerad') as install, \
                patch('auto_update.live_update_blockers', return_value=[]), \
                patch('auto_update.threading.Thread', side_effect=thread), \
                patch('auto_update.handoff_release') as handoff:
            auto_update.check_before_start('/app', parent=app, manual=True)
            callbacks.pop(0)()
            install.assert_not_called()
            handoff.assert_called_once_with(app, '/app', release)
            root.grab_set.assert_called_once()
            root.grab_release.assert_not_called()

    def test_permanent_processing_services_do_not_block_idle_update(self):
        app = self.app()
        for name in ('FFT-processor aktivering', 'Thread-3 (_process_queue)', 'FFmpeg-status', 'UploadStatusPoller'):
            thread = SimpleNamespace(name=name, is_alive=lambda: True)
            with patch('threading.enumerate', return_value=[thread]):
                self.assertEqual(live_update_blockers(app), [], name)

    def test_video_processing_flag_and_real_ffmpeg_process_still_block(self):
        app = self.app()
        app.plugins = {'video': SimpleNamespace(processing=True)}
        self.assertTrue(live_update_blockers(app))
        app.plugins = {'video': SimpleNamespace(processing=False, current_process=SimpleNamespace(poll=lambda: None))}
        self.assertTrue(live_update_blockers(app))
        app.plugins['video'].current_process.poll = lambda: 0
        self.assertEqual(live_update_blockers(app), [])

    def test_known_work_thread_still_blocks_until_finished(self):
        app = self.app()
        for name in ('PipelineThread', 'GenerateThread', 'MediaProcessingThread', 'Thread-2 (_process_all_worker)'):
            with patch('threading.enumerate', return_value=[SimpleNamespace(name=name, is_alive=lambda: True)]):
                self.assertIn(name, live_update_blockers(app))
