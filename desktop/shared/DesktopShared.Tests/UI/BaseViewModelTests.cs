using TTShared.UI;

namespace TTShared.Tests.UI;

public class BaseViewModelTests
{
    [Fact]
    public void SetProperty_ShouldNotify_WhenValueChanges()
    {
        var vm = new TestViewModel();
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName ?? "");

        vm.Name = "NewName";

        Assert.Contains("Name", changedProps);
        Assert.Equal("NewName", vm.Name);
    }

    [Fact]
    public void SetProperty_ShouldNotNotify_WhenValueSame()
    {
        var vm = new TestViewModel { Name = "Original" };
        var changedProps = new List<string>();
        vm.PropertyChanged += (_, e) => changedProps.Add(e.PropertyName ?? "");

        vm.Name = "Original"; // 相同值

        Assert.Empty(changedProps);
    }

    private class TestViewModel : BaseViewModel
    {
        private string _name = "";
        public string Name
        {
            get => _name;
            set => SetProperty(ref _name, value);
        }
    }
}
