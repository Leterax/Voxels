import multiprocessing
import struct
import time
import threading
from typing import Callable


class Writer(threading.Thread):
    def __init__(self, queue, buffer1, buffer2, toggle, should_write_event, done_flag):
        super().__init__()
        self.daemon = True

        (
            self.queue,
            self.buffer1,
            self.buffer2,
            self.toggle,
            self.should_write_event,
            self.done_flag,
        ) = (
            queue,
            buffer1,
            buffer2,
            toggle,
            should_write_event,
            done_flag,
        )

        self.start()

    def run(self) -> None:
        while True:
            if self.should_write_event.is_set():
                target_id, data = self.queue.get()
                buffer = self.buffer1 if self.toggle.is_set() else self.buffer2
                buffer.write(data, offset=3 * 4 * target_id)
                print(struct.unpack('f'*3*5, self.buffer1.read()))
                print(f'writing {data} to buffer {buffer} at offset: {3 * 4 * target_id}')
            else:
                self.done_flag.set()
                self.should_write_event.wait()


class Worker(multiprocessing.Process):
    def __init__(self, work_queue, output_queue):
        super().__init__()
        self.daemon = True

        self.work_queue = work_queue
        self.output_queue = output_queue

        self.start()

    def run(self) -> None:
        while True:
            target_id, new_pos = self.work_queue.get()
            # print(f"doing work on `{(target_id, new_pos)}`.")
            self.output_queue.put((target_id, new_pos))


class WorkerManager:
    def __init__(self, num_workers, buffer1, buffer2):
        self.num_workers = num_workers

        self.task_queue = multiprocessing.Queue()
        self.output_queue = multiprocessing.Queue()
        self.buffer_toggle = multiprocessing.Event()

        self.should_write_event = multiprocessing.Event()
        self.should_write_event.set()
        self.done_flag = multiprocessing.Event()

        self.writer = Writer(
            self.output_queue,
            buffer1,
            buffer2,
            self.buffer_toggle,
            self.should_write_event,
            self.done_flag,
        )

        self.workers = [
            Worker(self.task_queue, self.output_queue) for _ in range(num_workers)
        ]

    def add_item(self, item):
        self.task_queue.put(item)

    def join_all(self):
        while not self.task_queue.empty():
            time.sleep(0.25)
        self.kill_workers()

    def kill_workers(self):
        for worker in self.workers:
            worker.terminate()

    def wait_for_done(self, callback: Callable) -> None:
        """
        wait for Writer to finish current job, then call `callback`
        :param callback: callable to be called when done.
        """
        self.done_flag.wait()
        callback()

    def ask_switch_buffers(self, callback: Callable) -> None:
        """
        Asks Workers to switch to another buffer once they are done with their current task.
        """
        # tell workers to stop working
        self.should_write_event.clear()  # sets to False

        new_buffer = not self.buffer_toggle.is_set()

        def call_on_complete(self):
            self.switch_buffers(new_buffer)
            callback()

        threading.Thread(target=self.wait_for_done, args=(lambda: call_on_complete(self),)).start()

    def switch_buffers(self, new_buffer) -> None:
        """
        Switch buffers and allow workers to go back to work
        :param new_buffer:
        :return:
        """
        # at this
        if new_buffer == 1:
            self.buffer_toggle.set()
        if new_buffer == 0:
            self.buffer_toggle.clear()

        # reset done flags
        self.done_flag.clear()
        # resume work
        self.should_write_event.set()


if __name__ == "__main__":
    manager = WorkerManager(4)
    for number in range(100):
        manager.add_item(number)

    time.sleep(0.2)
    s = time.time()
    manager.ask_switch_buffers(1)
    print(time.time() - s)
    manager.join_all()
