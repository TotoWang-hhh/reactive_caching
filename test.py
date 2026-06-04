import reactive_caching
import time


class Rectangle(reactive_caching.CachedClass):

    def __init__(self):
        reactive_caching.CachedClass.__init__(self)
        self.width: int = 10
        self.height: int = 20
        
    @reactive_caching.cached_property(["width", "height"])
    def area(self) -> int:
        time.sleep(0.5)
        return self.width * self.height

    def timed_get_area(self) -> tuple[int, float]:
        start_time = time.perf_counter()
        area = self.area
        end_time = time.perf_counter()
        duration = end_time - start_time
        return area, duration

    def _on_cache_dirty(self, prop_name: str) -> None:
        print("Cache of area is now dirty! EWW!")


def print_result(test_no: int, rect: Rectangle, area: int, exe_time: float):
    exe_time = round(exe_time, 2)
    correct = rect.width * rect.height
    print(
        f"Test {test_no}: {rect.width=}, {rect.height=}, "
        f"{area=} ({"Pass" if area == correct else "Fail"}), "
        f"{exe_time=} ({"Cached" if exe_time < 0.5 else "Calced"})"
        )


print("==================================================")
print("Functionality test for Reactive Caching module")
print("--------------------------------------------------")
print("2026 by rgzz666")
print(f"Reactive Caching ver: {reactive_caching.__version__}")
print("- In this test, calculating area of rectangles is ")
print("  assumed as a time consuming operation.")
print("- Note that this is NOT a formal testcase.")
print("==================================================")

rect = Rectangle()

print(f"{rect._cached_rules=}")

area, exe_time = rect.timed_get_area()
print_result(1, rect, area, exe_time)

area, exe_time = rect.timed_get_area()
print_result(2, rect, area, exe_time)

rect.width = 30
area, exe_time = rect.timed_get_area()
print_result(3, rect, area, exe_time)